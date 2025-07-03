"""
SenseVoice 实时语音识别服务 - 主服务器文件
"""

import argparse
import asyncio
import traceback
import json
import time
import os
from typing import Optional
from urllib.parse import parse_qs

import uvicorn
import numpy as np
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from loguru import logger
from pydantic import BaseModel

from config import setup_logging, config
from model_service import model_service_lifespan, async_vad_generate, asr_async
from audio_buffer import AudioBuffer, CircularAudioBuffer
from speaker_recognition import diarize_speaker_online_improved_async
from text_processing import format_str_v3, contains_chinese_english_number
from recording_service import recording_processor
from database import db_manager
from ai_service import ai_service
from offline_processor import offline_processor


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


class RecordingProcessRequest(BaseModel):
    """录音处理请求模型"""
    speaker_count: int
    language: str = "zh"
    smart_punctuation: bool = True
    number_conversion: bool = True
    generate_summary: bool = True
    summary_type: str = "meeting"  # meeting, interview, lecture


class RecordingProcessResponse(BaseModel):
    """录音处理响应模型"""
    success: bool
    recording_id: Optional[str] = None
    message: str
    duration: Optional[float] = None
    error: Optional[str] = None


class RegenerateSummaryRequest(BaseModel):
    """重新生成摘要请求模型"""
    summary_type: str = "meeting"


class FrequentSpeakerRequest(BaseModel):
    """常用发言人请求模型"""
    name: str
    color: str = "#409eff"


class UpdateFrequentSpeakerRequest(BaseModel):
    """更新常用发言人请求模型"""
    name: Optional[str] = None
    color: Optional[str] = None


class UpdateSpeakerRequest(BaseModel):
    """更新发言人请求模型"""
    new_name: str
    setting_type: str = "single"  # single, global
    frequent_speaker_id: Optional[int] = None


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

# 挂载静态文件（HTML、CSS、JS等）
app.mount("/static", StaticFiles(directory="."), name="static")


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
    """返回前端主页面"""
    return FileResponse('index.html')

@app.get("/api")
async def api_info():
    """API信息端点"""
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


@app.post("/api/recordings/process", response_model=RecordingProcessResponse)
async def process_recording(
    audio_file: UploadFile = File(...),
    speaker_count: int = Form(...),
    language: str = Form("zh"),
    smart_punctuation: bool = Form(True),
    number_conversion: bool = Form(True),
    generate_summary: bool = Form(True),
    summary_type: str = Form("meeting")
):
    """提交录音进行处理"""
    try:
        # 验证文件类型
        logger.info(f"收到文件上传请求: filename={audio_file.filename}, content_type={audio_file.content_type}, size={audio_file.size}")
        if not audio_file.content_type or not audio_file.content_type.startswith(('audio/', 'video/')):
            logger.error(f"文件类型验证失败: {audio_file.content_type}")
            raise HTTPException(status_code=400, detail="请上传音频或视频文件")
        
        # 验证发言人数量（0表示自动识别）
        if speaker_count < 0 or speaker_count > 10:
            raise HTTPException(status_code=400, detail="发言人数量必须在0-10之间（0表示自动识别）")
        
        # 构建处理选项
        options = {
            "smart_punctuation": smart_punctuation,
            "number_conversion": number_conversion,
            "generate_summary": generate_summary,
            "summary_type": summary_type
        }
        
        # 处理录音
        result = await recording_processor.process_recording(
            audio_file=audio_file,
            speaker_count=speaker_count,
            language=language,
            options=options
        )
        
        return RecordingProcessResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理录音请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.get("/api/recordings/{recording_id}/status")
async def get_recording_status(recording_id: str):
    """获取录音处理状态"""
    try:
        status = await recording_processor.get_recording_status(recording_id)
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取录音状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@app.get("/api/recordings/{recording_id}/detail")
async def get_recording_detail(recording_id: str):
    """获取录音详情"""
    try:
        detail = db_manager.get_recording_detail(recording_id)
        if not detail:
            raise HTTPException(status_code=404, detail="录音记录不存在")
        
        return {
            "success": True,
            "data": detail
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取录音详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取详情失败: {str(e)}")


@app.get("/api/recordings")
async def get_recordings_list(page: int = 1, page_size: int = 20):
    """获取录音列表"""
    try:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
            
        result = db_manager.get_recordings_list(page=page, page_size=page_size)
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"获取录音列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@app.post("/api/recordings/{recording_id}/regenerate-summary")
async def regenerate_summary(recording_id: str, request: RegenerateSummaryRequest):
    """重新生成摘要"""
    try:
        result = await recording_processor.regenerate_summary(recording_id, request.summary_type)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新生成摘要失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重新生成摘要失败: {str(e)}")


@app.post("/api/recordings/{recording_id}/offline-reprocess")
async def offline_reprocess_recording(recording_id: str):
    """离线重新处理录音（高精度）"""
    try:
        logger.info(f"开始离线重新处理录音: {recording_id}")
        
        # 检查录音是否存在
        recording = db_manager.get_recording(recording_id)
        if not recording:
            raise HTTPException(status_code=404, detail="录音记录不存在")
        
        # 异步启动离线处理
        asyncio.create_task(offline_processor.reprocess_recording(recording_id))
        
        return {
            "success": True,
            "message": "离线重新处理已启动，请稍后查看结果",
            "recording_id": recording_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动离线重新处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")


@app.get("/api/recordings/{recording_id}/offline-status")
async def get_offline_processing_status(recording_id: str):
    """获取离线处理状态"""
    try:
        recording = db_manager.get_recording(recording_id)
        if not recording:
            raise HTTPException(status_code=404, detail="录音记录不存在")
        
        # 检查是否已经离线处理过
        segments = db_manager.get_segments(recording_id)
        has_offline_processed = any(
            segment.get("offline_processed", False) for segment in segments
        )
        
        return {
            "recording_id": recording_id,
            "status": recording["status"],
            "has_offline_processed": has_offline_processed,
            "can_reprocess": recording["status"] in ["completed", "offline_completed"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取离线处理状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@app.get("/api/recordings/{recording_id}/download")
async def download_recording(recording_id: str):
    """下载录音文件"""
    try:
        logger.info(f"开始下载录音文件: {recording_id}")
        
        recording = db_manager.get_recording(recording_id)
        if not recording:
            logger.error(f"录音记录不存在: {recording_id}")
            raise HTTPException(status_code=404, detail="录音记录不存在")
        
        file_path = recording.get("filePath")
        logger.info(f"获取到文件路径: {file_path}")
        
        if not file_path:
            logger.error(f"录音记录 {recording_id} 没有文件路径")
            raise HTTPException(status_code=404, detail="录音文件路径不存在")
            
        if not os.path.exists(file_path):
            logger.error(f"录音文件不存在于路径: {file_path}")
            raise HTTPException(status_code=404, detail=f"录音文件不存在: {file_path}")
        
        # 确定正确的媒体类型
        if file_path.lower().endswith('.wav'):
            media_type = 'audio/wav'
        elif file_path.lower().endswith('.mp3'):
            media_type = 'audio/mpeg'
        elif file_path.lower().endswith('.m4a'):
            media_type = 'audio/mp4'
        else:
            media_type = 'audio/wav'  # 默认为wav
        
        # 获取原始文件名
        original_filename = os.path.basename(file_path)
        
        return FileResponse(
            path=file_path,
            filename=original_filename,
            media_type=media_type,
            headers={
                "Content-Disposition": f'inline; filename="{original_filename}"',
                "Accept-Ranges": "bytes"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载录音文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@app.delete("/api/recordings/{recording_id}")
async def delete_recording(recording_id: str):
    """删除录音记录"""
    try:
        recording = db_manager.get_recording(recording_id)
        if not recording:
            raise HTTPException(status_code=404, detail="录音记录不存在")
        
        # 删除文件
        file_path = recording.get("filePath")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        # 删除数据库记录 (通过级联删除相关数据)
        from database import Recording
        with db_manager.get_session() as session:
            recording_obj = session.query(Recording).filter(
                Recording.id == recording_id
            ).first()
            if recording_obj:
                session.delete(recording_obj)
                session.commit()
        
        return {
            "success": True,
            "message": "录音已删除"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除录音失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ===== 发言人管理API =====

@app.get("/api/speakers/frequent")
async def get_frequent_speakers():
    """获取常用发言人列表"""
    try:
        speakers = db_manager.get_frequent_speakers()
        return {
            "success": True,
            "data": speakers,
            "total": len(speakers)
        }
    except Exception as e:
        logger.error(f"获取常用发言人失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@app.post("/api/speakers/frequent")
async def add_frequent_speaker(request: FrequentSpeakerRequest):
    """添加常用发言人"""
    try:
        speaker = db_manager.add_frequent_speaker(
            name=request.name,
            color=request.color
        )
        
        if speaker is None:
            raise HTTPException(status_code=400, detail="发言人名称已存在")
        
        return {
            "success": True,
            "data": speaker,
            "message": "添加成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加常用发言人失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


@app.put("/api/speakers/frequent/{speaker_id}")
async def update_frequent_speaker(speaker_id: int, request: UpdateFrequentSpeakerRequest):
    """更新常用发言人"""
    try:
        success = db_manager.update_frequent_speaker(
            speaker_id=speaker_id,
            name=request.name,
            color=request.color
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="发言人不存在")
        
        return {
            "success": True,
            "message": "更新成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新常用发言人失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@app.delete("/api/speakers/frequent/{speaker_id}")
async def delete_frequent_speaker(speaker_id: int):
    """删除常用发言人"""
    try:
        success = db_manager.delete_frequent_speaker(speaker_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="发言人不存在")
        
        return {
            "success": True,
            "message": "删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除常用发言人失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@app.post("/api/recordings/{recording_id}/speakers/{speaker_id}/update")
async def update_speaker_in_recording(recording_id: str, speaker_id: str, request: UpdateSpeakerRequest):
    """更新录音中的发言人信息"""
    try:
        # 验证录音是否存在
        recording = db_manager.get_recording(recording_id)
        if not recording:
            raise HTTPException(status_code=404, detail="录音不存在")
        
        # 验证设置类型
        if request.setting_type not in ["single", "global"]:
            raise HTTPException(status_code=400, detail="设置类型必须是 'single' 或 'global'")
        
        # 更新发言人信息
        success = db_manager.update_speaker_in_recording(
            recording_id=recording_id,
            speaker_id=speaker_id,
            new_name=request.new_name,
            setting_type=request.setting_type,
            frequent_speaker_id=request.frequent_speaker_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="更新失败")
        
        return {
            "success": True,
            "message": "发言人信息更新成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新发言人信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@app.get("/api/recordings/{recording_id}/speakers/settings-log")
async def get_speaker_settings_log(recording_id: str):
    """获取发言人设置日志"""
    try:
        # 验证录音是否存在
        recording = db_manager.get_recording(recording_id)
        if not recording:
            raise HTTPException(status_code=404, detail="录音不存在")
        
        logs = db_manager.get_speaker_settings_log(recording_id)
        
        return {
            "success": True,
            "data": logs,
            "total": len(logs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取发言人设置日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


@app.websocket("/ws/transcribe")
async def websocket_transcribe_endpoint(websocket: WebSocket):
    """
    WebSocket转录端点
    
    查询参数:
    - sv: 是否启用说话人验证 (true/false, 默认false)
    - lang: 语言设置 (auto/zh/en等, 默认auto)
    
    示例: ws://localhost:26000/ws/transcribe?sv=true&lang=auto
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
                                        
                                        # 生成最终数据（只包含纯文本，发言人信息通过单独字段传递）
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
    parser.add_argument('--port', type=int, default=26000, help='服务端口号')
    parser.add_argument('--host', type=str, default="0.0.0.0", help='服务主机地址')
    parser.add_argument('--certfile', type=str, help='SSL证书文件路径')
    parser.add_argument('--keyfile', type=str, help='SSL密钥文件路径')
    parser.add_argument('--workers', type=int, default=1, help='工作进程数')
    parser.add_argument('--log-level', type=str, default="info", 
                      choices=['debug', 'info', 'warning', 'error'],
                      help='日志级别')
    parser.add_argument('--env', type=str, default="auto", 
                      choices=['local', 'server', 'auto'],
                      help='运行环境: local(本地), server(服务器), auto(自动检测)')
    
    args = parser.parse_args()
    
    # 环境检测和配置
    if args.env == "auto":
        # 自动检测：如果提供了SSL证书，认为是服务器环境
        is_server = bool(args.certfile and args.keyfile)
    else:
        is_server = args.env == "server"
    
    # 根据环境调整默认配置
    if is_server:
        # 服务器环境：需要SSL证书
        if not args.certfile or not args.keyfile:
            logger.warning("服务器环境需要SSL证书，请提供 --certfile 和 --keyfile 参数")
            logger.info("示例: python main.py --env server --port 8989 --certfile /path/to/cert.pem --keyfile /path/to/key.pem")
        protocol = "wss" if (args.certfile and args.keyfile) else "ws"
        logger.info(f"🌐 服务器模式启动 ({protocol})")
    else:
        # 本地环境：不使用SSL
        protocol = "ws"
        logger.info("🏠 本地模式启动 (ws)")
    
    logger.info(f"启动SenseVoice实时语音识别服务...")
    logger.info(f"服务地址: {args.host}:{args.port}")
    logger.info(f"协议: {protocol}://")
    logger.info(f"配置信息: 采样率={config.sample_rate}Hz, 块大小={config.chunk_size_ms}ms")
    logger.info(f"说话人验证阈值: {config.sv_thr}")
    logger.info(f"线程池工作线程数: {config.thread_pool_max_workers}")
    
    # 启动服务
    try:
        run_kwargs = {
            "app": app,
            "host": args.host,
            "port": args.port,
            "log_level": args.log_level,
        }
        
        # 只有在服务器模式且提供了证书时才启用SSL
        if is_server and args.certfile and args.keyfile:
            run_kwargs["ssl_keyfile"] = args.keyfile
            run_kwargs["ssl_certfile"] = args.certfile
            logger.info(f"SSL已启用: 证书={args.certfile}, 密钥={args.keyfile}")
        
        if args.workers > 1:
            run_kwargs["workers"] = args.workers
            
        uvicorn.run(**run_kwargs)
    except Exception as e:
        logger.error(f"服务启动失败: {e}")
 