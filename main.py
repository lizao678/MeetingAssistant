"""
SenseVoice 实时语音识别服务 - 主服务器文件
"""

import argparse
import traceback
import json
import time
from typing import Optional
from urllib.parse import parse_qs

import uvicorn
import numpy as np
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from loguru import logger
from pydantic import BaseModel

from config import setup_logging, config
from model_service import model_service_lifespan, async_vad_generate, asr_async
from audio_buffer import AudioBuffer, CircularAudioBuffer
from speaker_recognition import diarize_speaker_online_improved_async
from text_processing import format_str_v3, contains_chinese_english_number


# 设置日志
setup_logging()


class TranscriptionResponse(BaseModel):
    """转录响应模型"""
    code: int
    msg: str
    data: str
    speaker_id: Optional[str] = None  # 说话人ID
    is_new_line: bool = False  # 是否需要换行
    segment_type: str = "continue"  # 段落类型: "new_speaker", "pause", "continue"
    timestamp: float = 0.0  # 时间戳


# 创建FastAPI应用
app = FastAPI(
    title="SenseVoice实时语音识别服务",
    description="基于SenseVoice的实时语音识别和说话人验证服务",
    version="2.0.0",
    lifespan=model_service_lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def custom_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
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
            msg=message,
            data=""
        ).model_dump()
    )


@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "service": "SenseVoice实时语音识别服务",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "实时语音识别",
            "说话人验证",
            "VAD检测",
            "多并发支持"
        ]
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "config": {
            "sample_rate": config.sample_rate,
            "chunk_size_ms": config.chunk_size_ms,
            "sv_threshold": config.sv_thr,
            "thread_pool_workers": config.thread_pool_max_workers
        }
    }


@app.websocket("/ws/transcribe")
async def websocket_transcribe_endpoint(websocket: WebSocket):
    """
    WebSocket转录端点
    
    查询参数:
    - sv: 是否启用说话人验证 (true/false, 默认false)
    - lang: 语言设置 (auto/zh/en等, 默认auto)
    
    示例: ws://localhost:27000/ws/transcribe?sv=true&lang=auto
    """
    try:
        # 解析查询参数
        query_params = parse_qs(websocket.scope['query_string'].decode())
        sv = query_params.get('sv', ['false'])[0].lower() in ['true', '1', 't', 'y', 'yes']
        lang = query_params.get('lang', ['auto'])[0].lower()
        
        await websocket.accept()

        # 为每个会话初始化状态
        chunk_size = int(config.chunk_size_ms * config.sample_rate / 1000)
        
        # 使用高效缓冲区
        audio_buffer = AudioBuffer(max_size=config.audio_buffer_max_size)
        vad_buffer_size = config.sample_rate * config.vad_buffer_seconds
        audio_vad = CircularAudioBuffer(max_samples=vad_buffer_size)
        
        cache_vad = {}
        cache_asr = {}
        last_vad_beg = last_vad_end = -1
        offset = 0
        
        # 为当前连接创建独立的声纹库和计数器
        speaker_gallery = {}
        speaker_counter = 0
        speaker_history = []
        current_speaker = None
        
        # 换行逻辑状态追踪
        last_speaker_id = None
        last_segment_end_time = 0.0
        pause_threshold_ms = config.pause_threshold_ms  # 从配置中获取停顿阈值
        
        buffer = b""
        logger.info(f"WebSocket session started with chunk_size={chunk_size}, vad_buffer_size={vad_buffer_size}")
        
        # VAD缓冲区管理
        last_activity_time = 0  # 最后活动时间
        total_processed_samples = 0  # 总处理样本数
        
        # 音频处理主循环
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
                total_processed_samples += chunk_size
                
                # 检查VAD缓冲区是否接近满容量，如果是则清理一部分
                if len(audio_vad) > vad_buffer_size * config.vad_buffer_cleanup_threshold:
                    cleanup_samples = int(vad_buffer_size * config.vad_buffer_cleanup_ratio)
                    audio_vad.pop_front(cleanup_samples)
                    offset += cleanup_samples / config.sample_rate * 1000
                    logger.debug(f"VAD buffer cleanup: removed {cleanup_samples} samples, new offset: {offset:.1f}ms")
                
                # 使用异步VAD推理
                res = await async_vad_generate(chunk, cache_vad, config.chunk_size_ms)
                
                # 检查长时间无语音活动，重置offset以避免累积误差
                silence_duration = (total_processed_samples - last_activity_time) / config.sample_rate
                if silence_duration > config.silence_reset_seconds:
                    logger.info(f"Long silence detected ({silence_duration:.1f}s), resetting VAD buffer offset")
                    # 保留最近几秒的音频数据
                    keep_samples = int(config.keep_audio_seconds * config.sample_rate)
                    if len(audio_vad) > keep_samples:
                        discard_samples = len(audio_vad) - keep_samples
                        audio_vad.pop_front(discard_samples)
                        offset += discard_samples / config.sample_rate * 1000
                    last_activity_time = total_processed_samples
                
                if len(res[0]["value"]):
                    for segment in res[0]["value"]:
                        if segment[0] > -1: 
                            last_vad_beg = segment[0]
                        if segment[1] > -1: 
                            last_vad_end = segment[1]
                        
                        if last_vad_beg > -1 and last_vad_end > -1:
                            # 更新最后活动时间
                            last_activity_time = total_processed_samples
                            
                            beg = int((last_vad_beg - offset) * config.sample_rate / 1000)
                            end = int((last_vad_end - offset) * config.sample_rate / 1000)
                            
                            # 确保索引不超出VAD缓冲区范围
                            vad_buffer_length = len(audio_vad)
                            if beg < vad_buffer_length and end > beg and beg >= 0:
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
                                        
                                        # 计算当前时间戳
                                        current_timestamp = time.time()
                                        current_segment_start_time = last_vad_beg  # VAD开始时间
                                        
                                        # 判断是否需要换行
                                        is_new_line = False
                                        segment_type = "continue"
                                        
                                        if config.enable_smart_line_break:
                                            # 智能换行模式
                                            # 1. 发言人变化检测
                                            if last_speaker_id is not None and speaker_id != last_speaker_id:
                                                is_new_line = True
                                                segment_type = "new_speaker"
                                                logger.info(f"Speaker changed: {last_speaker_id} -> {speaker_id}")
                                            
                                            # 2. 停顿检测（只有在同一发言人时才检测停顿）
                                            elif last_speaker_id == speaker_id and last_segment_end_time > 0:
                                                pause_duration = current_segment_start_time - last_segment_end_time
                                                if pause_duration > pause_threshold_ms:
                                                    is_new_line = True
                                                    segment_type = "pause"
                                                    logger.info(f"Long pause detected: {pause_duration:.1f}ms > {pause_threshold_ms}ms")
                                            
                                            # 3. 首次识别
                                            elif last_speaker_id is None:
                                                is_new_line = True
                                                segment_type = "new_speaker"
                                                logger.info(f"First speech segment from {speaker_id}")
                                        else:
                                            # 传统模式：每次都换行
                                            is_new_line = True
                                            segment_type = "traditional"
                                        
                                        # 生成最终数据
                                        if is_new_line:
                                            # 换行时包含说话人标识
                                            final_data = f"[{speaker_id}]: {formatted_text}"
                                        else:
                                            # 继续时只有文本
                                            final_data = formatted_text
                                        
                                        # 创建响应
                                        response = TranscriptionResponse(
                                            code=0,
                                            msg=json.dumps(result[0], ensure_ascii=False),
                                            data=final_data,
                                            speaker_id=speaker_id,
                                            is_new_line=is_new_line,
                                            segment_type=segment_type,
                                            timestamp=current_timestamp
                                        )
                                        await websocket.send_json(response.model_dump())
                                        
                                        # 更新状态
                                        last_speaker_id = speaker_id
                                        last_segment_end_time = last_vad_end
                                        
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行SenseVoice实时语音识别服务")
    parser.add_argument('--port', type=int, default=27000, help='服务端口号')
    parser.add_argument('--host', type=str, default="0.0.0.0", help='服务主机地址')
    parser.add_argument('--certfile', type=str, help='SSL证书文件路径')
    parser.add_argument('--keyfile', type=str, help='SSL密钥文件路径')
    parser.add_argument('--workers', type=int, default=1, help='工作进程数')
    parser.add_argument('--log-level', type=str, default="info", 
                      choices=['debug', 'info', 'warning', 'error'],
                      help='日志级别')
    
    args = parser.parse_args()
    
    logger.info(f"启动SenseVoice实时语音识别服务...")
    logger.info(f"服务地址: {args.host}:{args.port}")
    logger.info(f"配置信息: 采样率={config.sample_rate}Hz, 块大小={config.chunk_size_ms}ms")
    logger.info(f"说话人验证阈值: {config.sv_thr}")
    logger.info(f"线程池工作线程数: {config.thread_pool_max_workers}")
    
    # 启动服务
    try:
        uvicorn.run(
            app, 
            host=args.host, 
            port=args.port,
            log_level=args.log_level,
            workers=args.workers if args.workers > 1 else None,
            ssl_keyfile=args.keyfile,
            ssl_certfile=args.certfile
        )
    except Exception as e:
        logger.error(f"服务启动失败: {e}")
 