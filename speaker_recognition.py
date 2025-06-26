"""
说话人识别模块 - 处理说话人验证和识别功能
"""

import time
from typing import List, Optional, Tuple

import numpy as np
from loguru import logger

from config import config
from model_service import async_sv_pipeline


def check_audio_quality(audio_segment: np.ndarray, sample_rate: int = 16000) -> bool:
    """
    检查音频质量，确保适合进行说话人识别
    
    Args:
        audio_segment: 音频片段
        sample_rate: 采样率
        
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
    
    # 检查音频能量
    energy = np.mean(np.abs(audio_segment))
    if energy < 0.005:  # 降低能量阈值
        logger.debug(f"Audio energy {energy:.4f} too low for speaker verification")
        return False
    
    # 检查音频方差（避免静音或噪声）
    variance = np.var(audio_segment)
    if variance < 0.0005:  # 降低方差阈值
        logger.debug(f"Audio variance {variance:.6f} too low for speaker verification")
        return False
    
    return True


async def diarize_speaker_online_improved_async(
    audio_segment: np.ndarray, 
    speaker_gallery: dict, 
    speaker_counter: int, 
    sv_thr: float,
    speaker_history: Optional[List] = None, 
    current_speaker: Optional[str] = None
) -> Tuple[str, dict, int, List, str]:
    """
    改进的异步在线说话人日志分析函数
    
    Args:
        audio_segment: 当前的语音片段
        speaker_gallery: 当前会话的声纹库 {speaker_id: reference_audio}
        speaker_counter: 当前会话的说话人计数器
        sv_thr: 声纹比对的相似度阈值
        speaker_history: 说话人历史记录 [(speaker_id, confidence, timestamp), ...]
        current_speaker: 当前活跃的说话人
        
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
            dynamic_threshold = sv_thr * 1.1
            logger.debug(f"Raised threshold to {dynamic_threshold:.3f} for current speaker '{current_speaker}'")
    
    # 连续性判断
    if current_speaker and identified_speaker == current_speaker and best_score >= sv_thr * 0.6:
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
    
    # 检查是否应该创建新说话人
    # 只有当所有分数都明显低于阈值时才创建新说话人
    all_scores_low = all(score < sv_thr * 0.7 for score in scores.values())
    
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


def diarize_speaker_online_improved(
    audio_segment: np.ndarray, 
    speaker_gallery: dict, 
    speaker_counter: int, 
    sv_thr: float,
    speaker_history: Optional[List] = None, 
    current_speaker: Optional[str] = None
) -> Tuple[str, dict, int, List, str]:
    """
    改进的在线说话人日志分析函数（同步版本，保持兼容性）
    """
    import time
    from model_service import sv_pipeline
    
    # 初始化历史记录
    if speaker_history is None:
        speaker_history = []
    current_time = time.time()
    
    # 检查音频质量
    if not check_audio_quality(audio_segment):
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
    
    # 动态阈值调整
    dynamic_threshold = sv_thr
    
    if current_speaker and current_speaker in scores:
        current_score = scores[current_speaker]
        if current_score > sv_thr * 0.8:
            dynamic_threshold = sv_thr * 1.1
            logger.debug(f"Raised threshold to {dynamic_threshold:.3f} for current speaker '{current_speaker}'")
    
    # 连续性判断
    if current_speaker and identified_speaker == current_speaker and best_score >= sv_thr * 0.6:
        confidence = min(1.0, best_score)
        speaker_history.append((current_speaker, confidence, current_time))
        logger.info(f"Speaker continuity confirmed: '{current_speaker}' (score: {best_score:.4f})")
        return current_speaker, speaker_gallery, speaker_counter, speaker_history, current_speaker
    
    # 检查是否匹配到已有说话人
    if best_score >= dynamic_threshold:
        confidence = min(1.0, best_score)
        speaker_history.append((identified_speaker, confidence, current_time))
        logger.info(f"Matched existing speaker '{identified_speaker}' with score {best_score:.4f}")
        return identified_speaker, speaker_gallery, speaker_counter, speaker_history, identified_speaker
    
    # 检查是否应该创建新说话人
    all_scores_low = all(score < sv_thr * 0.7 for score in scores.values())
    
    if all_scores_low:
        speaker_counter += 1
        new_speaker_id = f"发言人{speaker_counter}"
        speaker_gallery[new_speaker_id] = audio_segment
        speaker_history.append((new_speaker_id, 0.8, current_time))
        logger.info(f"New speaker detected (all scores < {sv_thr * 0.7:.3f}). Assigning ID: {new_speaker_id}")
        return new_speaker_id, speaker_gallery, speaker_counter, speaker_history, new_speaker_id
    else:
        best_speaker = max(scores.items(), key=lambda x: x[1])[0]
        confidence = min(0.7, scores[best_speaker])
        speaker_history.append((best_speaker, confidence, current_time))
        logger.info(f"Using best match '{best_speaker}' with moderate confidence {scores[best_speaker]:.4f}")
        return best_speaker, speaker_gallery, speaker_counter, speaker_history, best_speaker


def diarize_speaker_online(audio_segment: np.ndarray, speaker_gallery: dict, speaker_counter: int, sv_thr: float):
    """
    兼容性包装函数，调用改进的说话人识别算法
    """
    result = diarize_speaker_online_improved(
        audio_segment, speaker_gallery, speaker_counter, sv_thr, 
        speaker_history=None, current_speaker=None
    )
    return result[0], result[1], result[2]  # 只返回前三个值以保持兼容性 