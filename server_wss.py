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

# --- 日志配置 (无改动) ---
logger.remove()
log_format = "{time:YYYY-MM-DD HH:mm:ss} [{level}] {file}:{line} - {message}"
logger.add(sys.stdout, format=log_format, level="DEBUG", filter=lambda record: record["level"].no < 40)
logger.add(sys.stderr, format=log_format, level="ERROR", filter=lambda record: record["level"].no >= 40)

# --- 全局配置 (无改动) ---
class Config(BaseSettings):
    sv_thr: float = Field(0.45, description="Speaker verification threshold for diarization") # 建议为在线日志调高阈值
    chunk_size_ms: int = Field(300, description="Chunk size in milliseconds")
    sample_rate: int = Field(16000, description="Sample rate in Hz")
    bit_depth: int = Field(16, description="Bit depth")
    channels: int = Field(1, description="Number of audio channels")
    avg_logprob_thr: float = Field(-0.25, description="average logprob threshold")

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


# --- 【已废弃】旧的全局说话人注册逻辑 ---
# reg_spks_files = [
#     "speaker/speaker1_a_cn_16k.wav"
# ]
# def reg_spk_init(files): ...
# reg_spks = reg_spk_init(reg_spks_files)


# --- 【新】在线说话人日志函数 ---
def diarize_speaker_online(audio_segment, speaker_gallery, speaker_counter, sv_thr):
    """
    对音频片段进行在线说话人日志分析。
    如果识别为新说话人，则更新声纹库。

    Args:
        audio_segment (np.ndarray): 当前的语音片段。
        speaker_gallery (dict): 当前会话的声纹库 {speaker_id: reference_audio}。
        speaker_counter (int): 当前会话的说话人计数器。
        sv_thr (float): 声纹比对的相似度阈值。

    Returns:
        tuple: (识别出的speaker_id, 更新后的speaker_gallery, 更新后的speaker_counter)
    """
    if not speaker_gallery:
        # 这是第一个说话人
        speaker_counter += 1
        speaker_id = f"发言人{speaker_counter}"
        speaker_gallery[speaker_id] = audio_segment
        logger.info(f"New speaker detected. Assigning ID: {speaker_id}")
        return speaker_id, speaker_gallery, speaker_counter

    best_score = -1.0
    identified_speaker = None

    # 与声纹库中已有的所有说话人进行比对
    for spk_id, ref_audio in speaker_gallery.items():
        try:
            res_sv = sv_pipeline([audio_segment, ref_audio])
            score = res_sv["score"]
            logger.debug(f"Comparing with '{spk_id}', score: {score:.4f}")
            if score > best_score:
                best_score = score
                identified_speaker = spk_id
        except Exception as e:
            logger.error(f"Error during speaker comparison with {spk_id}: {e}")
            continue

    if best_score >= sv_thr:
        # 匹配到已有说话人
        logger.info(f"Matched existing speaker '{identified_speaker}' with score {best_score:.4f}")
        return identified_speaker, speaker_gallery, speaker_counter
    else:
        # 这是一个新的说话人
        speaker_counter += 1
        new_speaker_id = f"发言人{speaker_counter}"
        speaker_gallery[new_speaker_id] = audio_segment
        logger.info(f"New speaker detected (best score {best_score:.4f} < threshold). Assigning ID: {new_speaker_id}")
        return new_speaker_id, speaker_gallery, speaker_counter


def asr(audio, lang, cache, use_itn=False):
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


# --- FastAPI 应用设置 (无改动) ---
app = FastAPI()
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
    info: str # 保持与原定义一致
    data: str

# 修正: 上方异常处理器中的content应与模型定义匹配
# class TranscriptionResponse(BaseModel):
#     code: int
#     msg: str  # 假设模型定义是msg
#     data: str


# --- 【修改后】WebSocket 端点 ---
@app.websocket("/ws/transcribe")
async def websocket_endpoint(websocket: WebSocket):
    try:
        query_params = parse_qs(websocket.scope['query_string'].decode())
        sv = query_params.get('sv', ['false'])[0].lower() in ['true', '1', 't', 'y', 'yes']
        lang = query_params.get('lang', ['auto'])[0].lower()
        
        await websocket.accept()

        # --- 为每个会话初始化状态 ---
        chunk_size = int(config.chunk_size_ms * config.sample_rate / 1000)
        audio_buffer = np.array([], dtype=np.float32)
        audio_vad = np.array([], dtype=np.float32)
        cache_vad = {}
        cache_asr = {}
        last_vad_beg = last_vad_end = -1
        offset = 0
        
        # 【新】为当前连接创建独立的声纹库和计数器
        speaker_gallery = {}  # key: "发言人1", value: np.ndarray (声纹音频)
        speaker_counter = 0
        
        buffer = b""
        while True:
            data = await websocket.receive_bytes()
            buffer += data
            if len(buffer) < 2:
                continue
                
            audio_buffer = np.append(
                audio_buffer, 
                np.frombuffer(buffer[:len(buffer) - (len(buffer) % 2)], dtype=np.int16).astype(np.float32) / 32767.0
            )
            buffer = buffer[len(buffer) - (len(buffer) % 2):]
   
            while len(audio_buffer) >= chunk_size:
                chunk = audio_buffer[:chunk_size]
                audio_buffer = audio_buffer[chunk_size:]
                audio_vad = np.append(audio_vad, chunk)
                
                res = model_vad.generate(input=chunk, cache=cache_vad, is_final=False, chunk_size=config.chunk_size_ms)
                
                if len(res[0]["value"]):
                    for segment in res[0]["value"]:
                        if segment[0] > -1: last_vad_beg = segment[0]
                        if segment[1] > -1: last_vad_end = segment[1]
                        if last_vad_beg > -1 and last_vad_end > -1:
                            beg = int((last_vad_beg - offset) * config.sample_rate / 1000)
                            end = int((last_vad_end - offset) * config.sample_rate / 1000)
                            
                            segment_audio = audio_vad[beg:end]
                            logger.info(f"[vad segment] audio_len: {len(segment_audio)}")

                            speaker_id = "发言人" # 默认ID
                            if sv and len(segment_audio) > 0:
                                # 1. 调用在线日志函数进行识别或注册
                                speaker_id, speaker_gallery, speaker_counter = diarize_speaker_online(
                                    segment_audio, speaker_gallery, speaker_counter, config.sv_thr
                                )
                            
                            # 2. 进行语音识别
                            result = asr(segment_audio, lang.strip(), cache_asr, True)
                            logger.info(f"asr response: {result}")
                            
                            audio_vad = audio_vad[end:]
                            offset = last_vad_end # 修正offset更新逻辑
                            last_vad_beg = last_vad_end = -1
                            
                            if result is not None and contains_chinese_english_number(result[0]['text']):
                                formatted_text = format_str_v3(result[0]['text'])
                                
                                # 3. 合并说话人ID和识别文本
                                final_data = f"[{speaker_id}]: {formatted_text}"
                                
                                response = TranscriptionResponse(
                                    code=0,
                                    info=json.dumps(result[0], ensure_ascii=False),
                                    data=final_data
                                )
                                await websocket.send_json(response.model_dump())
                                
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