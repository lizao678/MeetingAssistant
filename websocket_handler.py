"""
WebSocket处理模块 - 处理WebSocket连接和音频流处理
"""

import json
import traceback
from urllib.parse import parse_qs

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import BaseModel

from audio_buffer import AudioBuffer, CircularAudioBuffer
from config import config
from model_service import async_vad_generate, asr_async
from speaker_recognition import diarize_speaker_online_improved_async
from text_processing import format_str_v3, contains_chinese_english_number


class TranscriptionResponse(BaseModel):
    """转录响应模型"""
    code: int
    msg: str
    data: str


async def handle_websocket_transcription(websocket: WebSocket):
    """
    处理WebSocket转录请求的主要函数
    
    Args:
        websocket: WebSocket连接对象
    """
    try:
        # 解析查询参数
        query_params = parse_qs(websocket.scope['query_string'].decode())
        sv = query_params.get('sv', ['false'])[0].lower() in ['true', '1', 't', 'y', 'yes']
        lang = query_params.get('lang', ['auto'])[0].lower()
        
        await websocket.accept()

        # 为每个会话初始化状态
        chunk_size = int(config.chunk_size_ms * config.sample_rate / 1000)
        
        # 使用高效缓冲区：主缓冲区用于接收数据，VAD缓冲区存储更长时间的音频用于VAD分析
        audio_buffer = AudioBuffer(max_size=config.audio_buffer_max_size)
        vad_buffer_size = config.sample_rate * config.vad_buffer_duration_seconds
        audio_vad = CircularAudioBuffer(max_samples=vad_buffer_size)
        
        cache_vad = {}
        cache_asr = {}
        last_vad_beg = last_vad_end = -1
        offset = 0
        
        # 为当前连接创建独立的声纹库和计数器
        speaker_gallery = {}  # key: "发言人1", value: np.ndarray (声纹音频)
        speaker_counter = 0
        speaker_history = []  # 说话人历史记录
        current_speaker = None  # 当前活跃的说话人
        
        buffer = b""
        logger.info(f"WebSocket session started with chunk_size={chunk_size}, vad_buffer_size={vad_buffer_size}")
        
        # 音频处理主循环
        session_state = {
            'last_vad_beg': last_vad_beg,
            'last_vad_end': last_vad_end,
            'offset': offset,
            'speaker_gallery': speaker_gallery,
            'speaker_counter': speaker_counter,
            'speaker_history': speaker_history,
            'current_speaker': current_speaker
        }
        
        await _process_audio_stream(
            websocket, audio_buffer, audio_vad, chunk_size,
            cache_vad, cache_asr, session_state, sv, lang
        )
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Unexpected error: {e}\nCall stack:\n{traceback.format_exc()}")
        await websocket.close()
    finally:
        logger.info("Cleaned up resources after WebSocket disconnect")


async def _process_audio_stream(
    websocket: WebSocket,
    audio_buffer: AudioBuffer,
    audio_vad: CircularAudioBuffer,
    chunk_size: int,
    cache_vad: dict,
    cache_asr: dict,
    session_state: dict,
    sv: bool,
    lang: str
):
    """
    处理音频流的主要逻辑
    
    Args:
        websocket: WebSocket连接
        audio_buffer: 主音频缓冲区
        audio_vad: VAD音频缓冲区
        chunk_size: 音频块大小
        cache_vad: VAD缓存
        cache_asr: ASR缓存
        session_state: 会话状态字典
        sv: 是否启用说话人验证
        lang: 语言设置
    """
    buffer = b""
    
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
                    if segment[0] > -1: 
                        session_state['last_vad_beg'] = segment[0]
                    if segment[1] > -1: 
                        session_state['last_vad_end'] = segment[1]
                    
                    if session_state['last_vad_beg'] > -1 and session_state['last_vad_end'] > -1:
                        # 处理检测到的语音段
                        segment_result = await _process_speech_segment(
                            audio_vad, session_state['last_vad_beg'], session_state['last_vad_end'], 
                            session_state['offset'], session_state['speaker_gallery'], 
                            session_state['speaker_counter'], session_state['speaker_history'], 
                            session_state['current_speaker'], cache_asr, sv, lang, websocket
                        )
                        
                        if segment_result:
                            (session_state['speaker_gallery'], session_state['speaker_counter'], 
                             session_state['speaker_history'], session_state['current_speaker'], 
                             new_offset) = segment_result
                            
                            # 更新offset
                            if new_offset is not None:
                                session_state['offset'] = new_offset
                        
                        session_state['last_vad_beg'] = session_state['last_vad_end'] = -1


async def _process_speech_segment(
    audio_vad: CircularAudioBuffer,
    last_vad_beg: int,
    last_vad_end: int,
    offset: float,
    speaker_gallery: dict,
    speaker_counter: int,
    speaker_history: list,
    current_speaker: str,
    cache_asr: dict,
    sv: bool,
    lang: str,
    websocket: WebSocket
):
    """
    处理单个语音段
    
    Returns:
        tuple: (speaker_gallery, speaker_counter, speaker_history, current_speaker, new_offset)
               如果处理失败返回None
    """
    try:
        beg = int((last_vad_beg - offset) * config.sample_rate / 1000)
        end = int((last_vad_end - offset) * config.sample_rate / 1000)
        
        # 确保索引不超出VAD缓冲区范围
        vad_buffer_length = len(audio_vad)
        if beg < vad_buffer_length and end > beg:
            end = min(end, vad_buffer_length)
            segment_length = end - beg
            
            segment_audio = audio_vad.get_range(beg, segment_length)
            logger.info(f"[vad segment] audio_len: {len(segment_audio)}, beg: {beg}, end: {end}")

            speaker_id = "发言人"  # 默认ID
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
            
            # 进行异步语音识别
            try:
                result = await asr_async(segment_audio, lang.strip(), cache_asr, True)
                logger.info(f"asr response: {result}")
                
                if result is not None and contains_chinese_english_number(result[0]['text']):
                    formatted_text = format_str_v3(result[0]['text'])
                    
                    # 合并说话人ID和识别文本
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
                new_offset = offset + clear_length / config.sample_rate * 1000  # 转换为毫秒
            else:
                new_offset = None
            
            return speaker_gallery, speaker_counter, speaker_history, current_speaker, new_offset
            
    except Exception as e:
        logger.error(f"Error processing speech segment: {e}")
        
    return None 