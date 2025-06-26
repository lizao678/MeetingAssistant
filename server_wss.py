from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field
from funasr import AutoModel
import numpy as np
import soundfile as sf
import argparse
import uvicorn
from urllib.parse import parse_qs
import os
import re
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
from loguru import logger
import sys
import json
import traceback
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from collections import deque
from typing import List, Optional

# --- 高效音频缓冲区类 ---
class AudioBuffer:
    """
    高效的音频缓冲区实现，使用deque避免np.append的性能问题
    """
    def __init__(self, max_size: Optional[int] = None, dtype=np.float32):
        self.chunks = deque(maxlen=max_size)
        self.dtype = dtype
        self._total_length = 0
        
    def append(self, data: np.ndarray):
        """添加新的音频数据"""
        if len(data) > 0:
            self.chunks.append(data.astype(self.dtype))
            self._total_length += len(data)
    
    def get_data(self, start_idx: int = 0, length: Optional[int] = None) -> np.ndarray:
        """获取指定范围的音频数据"""
        if not self.chunks:
            return np.array([], dtype=self.dtype)
        
        # 合并所有chunks
        combined = np.concatenate(list(self.chunks))
        
        if length is None:
            return combined[start_idx:]
        else:
            end_idx = start_idx + length
            return combined[start_idx:min(end_idx, len(combined))]
    
    def pop_front(self, length: int) -> np.ndarray:
        """从前面弹出指定长度的数据"""
        if not self.chunks:
            return np.array([], dtype=self.dtype)
        
        result_data = []
        remaining_length = length
        
        while remaining_length > 0 and self.chunks:
            chunk = self.chunks[0]
            
            if len(chunk) <= remaining_length:
                # 整个chunk都要被弹出
                result_data.append(self.chunks.popleft())
                remaining_length -= len(chunk)
                self._total_length -= len(chunk)
            else:
                # 只弹出chunk的一部分
                result_data.append(chunk[:remaining_length])
                # 更新第一个chunk
                self.chunks[0] = chunk[remaining_length:]
                self._total_length -= remaining_length
                remaining_length = 0
        
        return np.concatenate(result_data) if result_data else np.array([], dtype=self.dtype)
    
    def __len__(self) -> int:
        """返回缓冲区中的总样本数"""
        return self._total_length
    
    def clear(self):
        """清空缓冲区"""
        self.chunks.clear()
        self._total_length = 0
    
    def slice_and_keep_rest(self, start_idx: int, end_idx: int) -> np.ndarray:
        """切片数据并保留剩余部分"""
        if not self.chunks:
            return np.array([], dtype=self.dtype)
        
        # 获取所有数据
        all_data = np.concatenate(list(self.chunks))
        
        # 提取指定范围的数据
        sliced_data = all_data[start_idx:end_idx]
        
        # 保留剩余数据
        remaining_data = all_data[end_idx:]
        
        # 重新设置缓冲区
        self.clear()
        if len(remaining_data) > 0:
            self.append(remaining_data)
        
        return sliced_data

class CircularAudioBuffer:
    """
    循环音频缓冲区，用于VAD处理，避免频繁的内存分配
    """
    def __init__(self, max_samples: int, dtype=np.float32):
        self.buffer = np.zeros(max_samples, dtype=dtype)
        self.max_samples = max_samples
        self.write_pos = 0
        self.read_pos = 0
        self.size = 0
        self.dtype = dtype
    
    def append(self, data: np.ndarray):
        """添加数据到循环缓冲区"""
        data = data.astype(self.dtype)
        data_len = len(data)
        
        # 如果数据太大，只保留最后的部分
        if data_len >= self.max_samples:
            self.buffer[:] = data[-self.max_samples:]
            self.write_pos = 0
            self.read_pos = 0
            self.size = self.max_samples
            return
        
        # 计算可用空间
        available_space = self.max_samples - self.size
        
        if data_len <= available_space:
            # 有足够空间，直接添加
            end_pos = self.write_pos + data_len
            if end_pos <= self.max_samples:
                self.buffer[self.write_pos:end_pos] = data
            else:
                # 需要环绕
                split_point = self.max_samples - self.write_pos
                self.buffer[self.write_pos:] = data[:split_point]
                self.buffer[:end_pos - self.max_samples] = data[split_point:]
            
            self.write_pos = end_pos % self.max_samples
            self.size += data_len
        else:
            # 空间不足，覆盖旧数据
            overwrite_count = data_len - available_space
            
            # 先添加到可用空间
            if available_space > 0:
                self.append(data[:available_space])
            
            # 然后覆盖旧数据
            self.read_pos = (self.read_pos + overwrite_count) % self.max_samples
            self.size -= overwrite_count
            
            # 添加剩余数据
            self.append(data[available_space:])
    
    def get_range(self, start_offset: int, length: int) -> np.ndarray:
        """获取指定范围的数据"""
        if length <= 0 or start_offset >= self.size:
            return np.array([], dtype=self.dtype)
        
        # 调整长度以不超过可用数据
        actual_length = min(length, self.size - start_offset)
        result = np.zeros(actual_length, dtype=self.dtype)
        
        start_pos = (self.read_pos + start_offset) % self.max_samples
        end_pos = start_pos + actual_length
        
        if end_pos <= self.max_samples:
            result[:] = self.buffer[start_pos:end_pos]
        else:
            # 需要环绕读取
            first_part_len = self.max_samples - start_pos
            result[:first_part_len] = self.buffer[start_pos:]
            result[first_part_len:] = self.buffer[:actual_length - first_part_len]
        
        return result
    
    def pop_front(self, length: int) -> np.ndarray:
        """从前面弹出数据"""
        if length <= 0 or self.size == 0:
            return np.array([], dtype=self.dtype)
        
        actual_length = min(length, self.size)
        result = self.get_range(0, actual_length)
        
        # 更新读取位置和大小
        self.read_pos = (self.read_pos + actual_length) % self.max_samples
        self.size -= actual_length
        
        return result
    
    def __len__(self) -> int:
        return self.size
    
    def clear(self):
        """清空缓冲区"""
        self.write_pos = 0
        self.read_pos = 0
        self.size = 0

# --- 线程池配置 ---
thread_pool_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="model_inference")

# --- 应用生命周期管理 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动
    logger.info("Application starting up...")
    yield
    # 应用关闭
    logger.info("Application shutting down...")
    thread_pool_executor.shutdown(wait=True)
    logger.info("Thread pool executor shut down")

# --- 日志配置 (无改动) ---
logger.remove()
log_format = "{time:YYYY-MM-DD HH:mm:ss} [{level}] {file}:{line} - {message}"
logger.add(sys.stdout, format=log_format, level="DEBUG", filter=lambda record: record["level"].no < 40)
logger.add(sys.stderr, format=log_format, level="ERROR", filter=lambda record: record["level"].no >= 40)

# --- 全局配置 (无改动) ---
class Config(BaseSettings):
    sv_thr: float = Field(0.42, description="Speaker verification threshold for diarization") # 提高阈值，平衡精度和召回
    chunk_size_ms: int = Field(300, description="Chunk size in milliseconds")
    sample_rate: int = Field(16000, description="Sample rate in Hz")
    bit_depth: int = Field(16, description="Bit depth")
    channels: int = Field(1, description="Number of audio channels")
    avg_logprob_thr: float = Field(-0.25, description="average logprob threshold")
    # 新增说话人识别相关配置
    min_audio_length_ms: int = Field(800, description="Minimum audio length for speaker verification in milliseconds")  # 降低最小长度要求
    max_audio_length_ms: int = Field(5000, description="Maximum audio length for speaker verification in milliseconds")
    speaker_continuity_threshold: int = Field(3, description="Number of consecutive segments to confirm speaker identity")
    confidence_decay: float = Field(0.95, description="Confidence decay factor for speaker continuity")

config = Config()

# --- 文本格式化相关 (无改动) ---
# ... (此处省略 emo_dict, event_dict, emoji_dict, lang_dict 等字典和格式化函数，与您原代码相同)
emo_dict = {
    "<|HAPPY|>": "😊", "<|SAD|>": "😔", "<|ANGRY|>": "😡", "<|NEUTRAL|>": "",
    "<|FEARFUL|>": "😰", "<|DISGUSTED|>": "🤢", "<|SURPRISED|>": "😮",
}
event_dict = {
    "<|BGM|>": "🎼", "<|Speech|>": "", "<|Applause|>": "👏", "<|Laughter|>": "😀",
    "<|Cry|>": "😭", "<|Sneeze|>": "🤧", "<|Breath|>": "", "<|Cough|>": "🤧",
}
emoji_dict = {
    "<|nospeech|><|Event_UNK|>": "❓", "<|zh|>": "", "<|en|>": "", "<|yue|>": "",
    "<|ja|>": "", "<|ko|>": "", "<|nospeech|>": "", "<|HAPPY|>": "😊", "<|SAD|>": "😔",
    "<|ANGRY|>": "😡", "<|NEUTRAL|>": "", "<|BGM|>": "🎼", "<|Speech|>": "",
    "<|Applause|>": "👏", "<|Laughter|>": "😀", "<|FEARFUL|>": "😰",
    "<|DISGUSTED|>": "🤢", "<|SURPRISED|>": "😮", "<|Cry|>": "😭", "<|EMO_UNKNOWN|>": "",
    "<|Sneeze|>": "🤧", "<|Breath|>": "", "<|Cough|>": "😷", "<|Sing|>": "",
    "<|Speech_Noise|>": "", "<|withitn|>": "", "<|woitn|>": "", "<|GBG|>": "", "<|Event_UNK|>": "",
}
lang_dict = {
    "<|zh|>": "<|lang|>", "<|en|>": "<|lang|>", "<|yue|>": "<|lang|>",
    "<|ja|>": "<|lang|>", "<|ko|>": "<|lang|>", "<|nospeech|>": "<|lang|>",
}
emo_set = {"😊", "😔", "😡", "😰", "🤢", "😮"}
event_set = {"🎼", "👏", "😀", "😭", "🤧", "😷"}

def format_str(s):
    for sptk in emoji_dict:
        s = s.replace(sptk, emoji_dict[sptk])
    return s

def format_str_v2(s):
    sptk_dict = {}
    for sptk in emoji_dict:
        sptk_dict[sptk] = s.count(sptk)
        s = s.replace(sptk, "")
    emo = "<|NEUTRAL|>"
    for e in emo_dict:
        if sptk_dict[e] > sptk_dict[emo]:
            emo = e
    for e in event_dict:
        if sptk_dict[e] > 0:
            s = event_dict[e] + s
    s = s + emo_dict[emo]
    for emoji in emo_set.union(event_set):
        s = s.replace(" " + emoji, emoji)
        s = s.replace(emoji + " ", emoji)
    return s.strip()

def format_str_v3(s):
    def get_emo(s):
        return s[-1] if s[-1] in emo_set else None
    def get_event(s):
        return s[0] if s[0] in event_set else None
    s = s.replace("<|nospeech|><|Event_UNK|>", "❓")
    for lang in lang_dict:
        s = s.replace(lang, "<|lang|>")
    s_list = [format_str_v2(s_i).strip(" ") for s_i in s.split("<|lang|>")]
    new_s = " " + s_list[0]
    cur_ent_event = get_event(new_s)
    for i in range(1, len(s_list)):
        if len(s_list[i]) == 0:
            continue
        if get_event(s_list[i]) == cur_ent_event and get_event(s_list[i]) != None:
            s_list[i] = s_list[i][1:]
        cur_ent_event = get_event(s_list[i])
        if get_emo(s_list[i]) != None and get_emo(s_list[i]) == get_emo(new_s):
            new_s = new_s[:-1]
        new_s += s_list[i].strip().lstrip()
    new_s = new_s.replace("The.", " ")
    return new_s.strip()

def contains_chinese_english_number(s: str) -> bool:
    return bool(re.search(r'[\u4e00-\u9fffA-Za-z0-9]', s))


# --- 模型加载 (无改动) ---
sv_pipeline = pipeline(
    task='speaker-verification',
    model='iic/speech_eres2net_large_sv_zh-cn_3dspeaker_16k',
    model_revision='v1.0.0'
)
model_asr = AutoModel(
    model="iic/SenseVoiceSmall",
    trust_remote_code=True,
    remote_code="./model.py",
    device="cuda:0",
    disable_update=True
)
model_vad = AutoModel(
    model="fsmn-vad",
    model_revision="v2.0.4",
    disable_pbar=True,
    max_end_silence_time=500,
    disable_update=True,
)


# --- 异步模型推理包装函数 ---
async def async_vad_generate(chunk, cache_vad, chunk_size_ms):
    """异步VAD推理"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool_executor,
        lambda: model_vad.generate(input=chunk, cache=cache_vad, is_final=False, chunk_size=chunk_size_ms)
    )

async def async_sv_pipeline(audio_pair):
    """异步说话人验证"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool_executor,
        lambda: sv_pipeline(audio_pair)
    )

async def async_asr_generate(audio, lang, cache, use_itn=False):
    """异步语音识别"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool_executor,
        lambda: model_asr.generate(
            input=audio,
            cache=cache,
            language=lang.strip(),
            use_itn=use_itn,
            batch_size_s=60,
        )
    )

# --- 【已废弃】旧的全局说话人注册逻辑 ---
# reg_spks_files = [
#     "speaker/speaker1_a_cn_16k.wav"
# ]
# def reg_spk_init(files): ...
# reg_spks = reg_spk_init(reg_spks_files)


# --- 【改进】在线说话人日志函数 ---
def check_audio_quality(audio_segment, sample_rate=16000):
    """
    检查音频质量，确保适合进行说话人识别
    
    Args:
        audio_segment (np.ndarray): 音频片段
        sample_rate (int): 采样率
        
    Returns:
        bool: 音频质量是否合格
    """
    if len(audio_segment) == 0:
        return False
    
    # 检查音频长度
    duration_ms = len(audio_segment) / sample_rate * 1000
    if duration_ms < config.min_audio_length_ms or duration_ms > config.max_audio_length_ms:
        logger.debug(f"Audio duration {duration_ms:.1f}ms not suitable for speaker verification")
        return False
    
    # 检查音频能量 - 降低要求
    energy = np.mean(np.abs(audio_segment))
    if energy < 0.005:  # 降低能量阈值（原值：0.01）
        logger.debug(f"Audio energy {energy:.4f} too low for speaker verification")
        return False
    
    # 检查音频方差（避免静音或噪声）- 降低要求
    variance = np.var(audio_segment)
    if variance < 0.0005:  # 降低方差阈值（原值：0.001）
        logger.debug(f"Audio variance {variance:.6f} too low for speaker verification")
        return False
    
    return True

async def diarize_speaker_online_improved_async(audio_segment, speaker_gallery, speaker_counter, sv_thr, 
                                               speaker_history=None, current_speaker=None):
    """
    改进的异步在线说话人日志分析函数
    
    Args:
        audio_segment (np.ndarray): 当前的语音片段
        speaker_gallery (dict): 当前会话的声纹库 {speaker_id: reference_audio}
        speaker_counter (int): 当前会话的说话人计数器
        sv_thr (float): 声纹比对的相似度阈值
        speaker_history (list): 说话人历史记录 [(speaker_id, confidence, timestamp), ...]
        current_speaker (str): 当前活跃的说话人
        
    Returns:
        tuple: (识别出的speaker_id, 更新后的speaker_gallery, 更新后的speaker_counter, 
                更新后的speaker_history, 更新后的current_speaker)
    """
    current_time = time.time()
    
    # 初始化历史记录
    if speaker_history is None:
        speaker_history = []
    
    # 检查音频质量
    if not check_audio_quality(audio_segment):
        # 音频质量不合格，使用当前说话人或默认值
        if current_speaker:
            logger.debug(f"Using current speaker '{current_speaker}' due to poor audio quality")
            return current_speaker, speaker_gallery, speaker_counter, speaker_history, current_speaker
        else:
            return "发言人", speaker_gallery, speaker_counter, speaker_history, current_speaker
    
    # 如果是第一个说话人
    if not speaker_gallery:
        speaker_counter += 1
        speaker_id = f"发言人{speaker_counter}"
        speaker_gallery[speaker_id] = audio_segment
        speaker_history.append((speaker_id, 1.0, current_time))
        logger.info(f"First speaker detected. Assigning ID: {speaker_id}")
        return speaker_id, speaker_gallery, speaker_counter, speaker_history, speaker_id
    
    # 与声纹库中的所有说话人进行并发比对
    comparison_tasks = []
    speaker_ids = list(speaker_gallery.keys())
    
    for spk_id in speaker_ids:
        ref_audio = speaker_gallery[spk_id]
        task = async_sv_pipeline([audio_segment, ref_audio])
        comparison_tasks.append((spk_id, task))
    
    # 并发执行所有说话人验证
    best_score = -1.0
    identified_speaker = None
    scores = {}
    
    try:
        for spk_id, task in comparison_tasks:
            try:
                res_sv = await task
                score = res_sv["score"]
                scores[spk_id] = score
                logger.debug(f"Comparing with '{spk_id}', score: {score:.4f}")
                if score > best_score:
                    best_score = score
                    identified_speaker = spk_id
            except Exception as e:
                logger.error(f"Error during speaker comparison with {spk_id}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error during concurrent speaker verification: {e}")
        # 如果并发比对失败，使用当前说话人或默认值
        if current_speaker:
            return current_speaker, speaker_gallery, speaker_counter, speaker_history, current_speaker
        else:
            return "发言人", speaker_gallery, speaker_counter, speaker_history, current_speaker
    
    # 动态阈值调整：基于历史记录和当前说话人
    dynamic_threshold = sv_thr
    
    # 如果当前有活跃说话人，降低切换阈值
    if current_speaker and current_speaker in scores:
        current_score = scores[current_speaker]
        # 如果当前说话人分数较高，提高切换阈值
        if current_score > sv_thr * 0.8:
            dynamic_threshold = sv_thr * 1.1  # 降低阈值提升倍数（原值：1.2）
            logger.debug(f"Raised threshold to {dynamic_threshold:.3f} for current speaker '{current_speaker}'")
    
    # 连续性判断 - 降低严格程度
    if current_speaker and identified_speaker == current_speaker and best_score >= sv_thr * 0.6:  # 降低连续性阈值（原值：0.7）
        # 连续说话，保持当前说话人
        confidence = min(1.0, best_score)
        speaker_history.append((current_speaker, confidence, current_time))
        logger.info(f"Speaker continuity confirmed: '{current_speaker}' (score: {best_score:.4f})")
        return current_speaker, speaker_gallery, speaker_counter, speaker_history, current_speaker
    
    # 检查是否匹配到已有说话人
    if best_score >= dynamic_threshold:
        # 匹配到已有说话人
        confidence = min(1.0, best_score)
        speaker_history.append((identified_speaker, confidence, current_time))
        logger.info(f"Matched existing speaker '{identified_speaker}' with score {best_score:.4f}")
        return identified_speaker, speaker_gallery, speaker_counter, speaker_history, identified_speaker
    
    # 检查是否应该创建新说话人 - 降低创建新说话人的门槛
    # 只有当所有分数都明显低于阈值时才创建新说话人
    all_scores_low = all(score < sv_thr * 0.7 for score in scores.values())  # 降低门槛（原值：0.8）
    
    if all_scores_low:
        # 创建新说话人
        speaker_counter += 1
        new_speaker_id = f"发言人{speaker_counter}"
        speaker_gallery[new_speaker_id] = audio_segment
        speaker_history.append((new_speaker_id, 0.8, current_time))
        logger.info(f"New speaker detected (all scores < {sv_thr * 0.7:.3f}). Assigning ID: {new_speaker_id}")
        return new_speaker_id, speaker_gallery, speaker_counter, speaker_history, new_speaker_id
    else:
        # 分数不够高但也不够低，使用最佳匹配
        best_speaker = max(scores.items(), key=lambda x: x[1])[0]
        confidence = min(0.7, scores[best_speaker])
        speaker_history.append((best_speaker, confidence, current_time))
        logger.info(f"Using best match '{best_speaker}' with moderate confidence {scores[best_speaker]:.4f}")
        return best_speaker, speaker_gallery, speaker_counter, speaker_history, best_speaker

# 保留原函数名以兼容现有代码（同步版本）
def diarize_speaker_online_improved(audio_segment, speaker_gallery, speaker_counter, sv_thr, 
                                   speaker_history=None, current_speaker=None):
    """
    改进的在线说话人日志分析函数（同步版本，保持兼容性）
    """
    import time
    
    # 初始化历史记录
    if speaker_history is None:
        speaker_history = []
    current_time = time.time()
    
    # 检查音频质量
    if not check_audio_quality(audio_segment):
        # 音频质量不合格，使用当前说话人或默认值
        if current_speaker:
            logger.debug(f"Using current speaker '{current_speaker}' due to poor audio quality")
            return current_speaker, speaker_gallery, speaker_counter, speaker_history, current_speaker
        else:
            return "发言人", speaker_gallery, speaker_counter, speaker_history, current_speaker
    
    # 如果是第一个说话人
    if not speaker_gallery:
        speaker_counter += 1
        speaker_id = f"发言人{speaker_counter}"
        speaker_gallery[speaker_id] = audio_segment
        speaker_history.append((speaker_id, 1.0, current_time))
        logger.info(f"First speaker detected. Assigning ID: {speaker_id}")
        return speaker_id, speaker_gallery, speaker_counter, speaker_history, speaker_id
    
    # 与声纹库中的所有说话人进行比对
    best_score = -1.0
    identified_speaker = None
    scores = {}
    
    for spk_id, ref_audio in speaker_gallery.items():
        try:
            res_sv = sv_pipeline([audio_segment, ref_audio])
            score = res_sv["score"]
            scores[spk_id] = score
            logger.debug(f"Comparing with '{spk_id}', score: {score:.4f}")
            if score > best_score:
                best_score = score
                identified_speaker = spk_id
        except Exception as e:
            logger.error(f"Error during speaker comparison with {spk_id}: {e}")
            continue
    
    # 动态阈值调整：基于历史记录和当前说话人
    dynamic_threshold = sv_thr
    
    # 如果当前有活跃说话人，降低切换阈值
    if current_speaker and current_speaker in scores:
        current_score = scores[current_speaker]
        # 如果当前说话人分数较高，提高切换阈值
        if current_score > sv_thr * 0.8:
            dynamic_threshold = sv_thr * 1.1  # 降低阈值提升倍数（原值：1.2）
            logger.debug(f"Raised threshold to {dynamic_threshold:.3f} for current speaker '{current_speaker}'")
    
    # 连续性判断 - 降低严格程度
    if current_speaker and identified_speaker == current_speaker and best_score >= sv_thr * 0.6:  # 降低连续性阈值（原值：0.7）
        # 连续说话，保持当前说话人
        confidence = min(1.0, best_score)
        speaker_history.append((current_speaker, confidence, current_time))
        logger.info(f"Speaker continuity confirmed: '{current_speaker}' (score: {best_score:.4f})")
        return current_speaker, speaker_gallery, speaker_counter, speaker_history, current_speaker
    
    # 检查是否匹配到已有说话人
    if best_score >= dynamic_threshold:
        # 匹配到已有说话人
        confidence = min(1.0, best_score)
        speaker_history.append((identified_speaker, confidence, current_time))
        logger.info(f"Matched existing speaker '{identified_speaker}' with score {best_score:.4f}")
        return identified_speaker, speaker_gallery, speaker_counter, speaker_history, identified_speaker
    
    # 检查是否应该创建新说话人 - 降低创建新说话人的门槛
    # 只有当所有分数都明显低于阈值时才创建新说话人
    all_scores_low = all(score < sv_thr * 0.7 for score in scores.values())  # 降低门槛（原值：0.8）
    
    if all_scores_low:
        # 创建新说话人
        speaker_counter += 1
        new_speaker_id = f"发言人{speaker_counter}"
        speaker_gallery[new_speaker_id] = audio_segment
        speaker_history.append((new_speaker_id, 0.8, current_time))
        logger.info(f"New speaker detected (all scores < {sv_thr * 0.7:.3f}). Assigning ID: {new_speaker_id}")
        return new_speaker_id, speaker_gallery, speaker_counter, speaker_history, new_speaker_id
    else:
        # 分数不够高但也不够低，使用最佳匹配
        best_speaker = max(scores.items(), key=lambda x: x[1])[0]
        confidence = min(0.7, scores[best_speaker])
        speaker_history.append((best_speaker, confidence, current_time))
        logger.info(f"Using best match '{best_speaker}' with moderate confidence {scores[best_speaker]:.4f}")
        return best_speaker, speaker_gallery, speaker_counter, speaker_history, best_speaker

# 保留原函数名以兼容现有代码
def diarize_speaker_online(audio_segment, speaker_gallery, speaker_counter, sv_thr):
    """
    兼容性包装函数，调用改进的说话人识别算法
    """
    result = diarize_speaker_online_improved(
        audio_segment, speaker_gallery, speaker_counter, sv_thr, 
        speaker_history=None, current_speaker=None
    )
    return result[0], result[1], result[2]  # 只返回前三个值以保持兼容性


async def asr_async(audio, lang, cache, use_itn=False):
    """异步语音识别函数"""
    start_time = time.time()
    result = await async_asr_generate(audio, lang, cache, use_itn)
    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.debug(f"asr elapsed: {elapsed_time * 1000:.2f} milliseconds")
    return result

def asr(audio, lang, cache, use_itn=False):
    """保持原有同步函数以兼容其他地方的调用"""
    start_time = time.time()
    result = model_asr.generate(
        input=audio,
        cache=cache,
        language=lang.strip(),
        use_itn=use_itn,
        batch_size_s=60,
    )
    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.debug(f"asr elapsed: {elapsed_time * 1000:.2f} milliseconds")
    return result


# --- FastAPI 应用设置 ---
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
@app.exception_handler(Exception)
async def custom_exception_handler(request: Request, exc: Exception):
    # ... (此处省略异常处理代码, 与您原代码相同)
    logger.error("Exception occurred", exc_info=True)
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        message = exc.detail
    elif isinstance(exc, RequestValidationError):
        status_code = HTTP_422_UNPROCESSABLE_ENTITY
        message = "Validation error: " + str(exc.errors())
    else:
        status_code = 500
        message = "Internal server error: " + str(exc)
    
    return JSONResponse(
        status_code=status_code,
        content=TranscriptionResponse(
            code=status_code,
            msg=message, # 修正: 原代码此处为info, 改为msg以匹配模型定义
            data=""
        ).model_dump()
    )

class TranscriptionResponse(BaseModel):
    code: int
    msg: str # 保持与原定义一致
    data: str

# 修正: 上方异常处理器中的content应与模型定义匹配
# class TranscriptionResponse(BaseModel):
#     code: int
#     msg: str  # 假设模型定义是msg
#     data: str


# --- 【优化后】WebSocket 端点 ---
@app.websocket("/ws/transcribe")
async def websocket_endpoint(websocket: WebSocket):
    try:
        query_params = parse_qs(websocket.scope['query_string'].decode())
        sv = query_params.get('sv', ['false'])[0].lower() in ['true', '1', 't', 'y', 'yes']
        lang = query_params.get('lang', ['auto'])[0].lower()
        
        await websocket.accept()

        # --- 为每个会话初始化状态 ---
        chunk_size = int(config.chunk_size_ms * config.sample_rate / 1000)
        
        # 使用高效缓冲区：主缓冲区用于接收数据，VAD缓冲区存储更长时间的音频用于VAD分析
        audio_buffer = AudioBuffer(max_size=100)  # 主音频接收缓冲区
        vad_buffer_size = config.sample_rate * 10  # 10秒的VAD缓冲区
        audio_vad = CircularAudioBuffer(max_samples=vad_buffer_size)
        
        cache_vad = {}
        cache_asr = {}
        last_vad_beg = last_vad_end = -1
        offset = 0
        
        # 【改进】为当前连接创建独立的声纹库和计数器
        speaker_gallery = {}  # key: "发言人1", value: np.ndarray (声纹音频)
        speaker_counter = 0
        speaker_history = []  # 说话人历史记录
        current_speaker = None  # 当前活跃的说话人
        
        buffer = b""
        logger.info(f"WebSocket session started with chunk_size={chunk_size}, vad_buffer_size={vad_buffer_size}")
        
        while True:
            data = await websocket.receive_bytes()
            buffer += data
            if len(buffer) < 2:
                continue
                
            # 将字节数据转换为浮点数音频数据
            new_audio_data = np.frombuffer(
                buffer[:len(buffer) - (len(buffer) % 2)], 
                dtype=np.int16
            ).astype(np.float32) / 32767.0
            
            audio_buffer.append(new_audio_data)
            buffer = buffer[len(buffer) - (len(buffer) % 2):]
   
            # 处理音频chunk
            while len(audio_buffer) >= chunk_size:
                # 从主缓冲区获取一个chunk
                chunk = audio_buffer.pop_front(chunk_size)
                
                # 将chunk添加到VAD缓冲区
                audio_vad.append(chunk)
                
                # 使用异步VAD推理
                res = await async_vad_generate(chunk, cache_vad, config.chunk_size_ms)
                
                if len(res[0]["value"]):
                    for segment in res[0]["value"]:
                        if segment[0] > -1: last_vad_beg = segment[0]
                        if segment[1] > -1: last_vad_end = segment[1]
                        if last_vad_beg > -1 and last_vad_end > -1:
                            beg = int((last_vad_beg - offset) * config.sample_rate / 1000)
                            end = int((last_vad_end - offset) * config.sample_rate / 1000)
                            
                            # 确保索引不超出VAD缓冲区范围
                            vad_buffer_length = len(audio_vad)
                            if beg < vad_buffer_length and end > beg:
                                end = min(end, vad_buffer_length)
                                segment_length = end - beg
                                
                                segment_audio = audio_vad.get_range(beg, segment_length)
                                logger.info(f"[vad segment] audio_len: {len(segment_audio)}, beg: {beg}, end: {end}")

                                speaker_id = "发言人" # 默认ID
                                if sv and len(segment_audio) > 0:
                                    # 使用改进的异步说话人识别算法
                                    try:
                                        speaker_id, speaker_gallery, speaker_counter, speaker_history, current_speaker = await diarize_speaker_online_improved_async(
                                            segment_audio, speaker_gallery, speaker_counter, config.sv_thr,
                                            speaker_history, current_speaker
                                        )
                                    except Exception as e:
                                        logger.error(f"Speaker verification error: {e}")
                                        speaker_id = "发言人"
                                
                                # 2. 进行异步语音识别
                                try:
                                    result = await asr_async(segment_audio, lang.strip(), cache_asr, True)
                                    logger.info(f"asr response: {result}")
                                    
                                    if result is not None and contains_chinese_english_number(result[0]['text']):
                                        formatted_text = format_str_v3(result[0]['text'])
                                        
                                        # 3. 合并说话人ID和识别文本
                                        final_data = f"[{speaker_id}]: {formatted_text}"
                                        
                                        response = TranscriptionResponse(
                                            code=0,
                                            msg=json.dumps(result[0], ensure_ascii=False),
                                            data=final_data
                                        )
                                        await websocket.send_json(response.model_dump())
                                        
                                except Exception as e:
                                    logger.error(f"ASR processing error: {e}")
                                
                                # 清理已处理的VAD数据（保留一些重叠以确保连续性）
                                overlap_samples = int(0.1 * config.sample_rate)  # 100ms重叠
                                clear_length = max(0, end - overlap_samples)
                                if clear_length > 0:
                                    audio_vad.pop_front(clear_length)
                                    offset += clear_length / config.sample_rate * 1000  # 转换为毫秒
                                
                                last_vad_beg = last_vad_end = -1
                                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Unexpected error: {e}\nCall stack:\n{traceback.format_exc()}")
        await websocket.close()
    finally:
        logger.info("Cleaned up resources after WebSocket disconnect")


# --- 服务启动 (无改动) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the FastAPI app with a specified port.")
    parser.add_argument('--port', type=int, default=27000, help='Port number to run the FastAPI app on.')
    parser.add_argument('--certfile', type=str, default='path_to_your_certfile', help='SSL certificate file')
    parser.add_argument('--keyfile', type=str, default='path_to_your_keyfile', help='SSL key file')
    args = parser.parse_args()

    uvicorn.run(app, host="0.0.0.0", port=args.port)