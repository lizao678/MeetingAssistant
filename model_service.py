"""
模型服务模块 - 管理和调用AI模型
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Optional

import numpy as np
from funasr import AutoModel
from loguru import logger
from modelscope.pipelines import pipeline

from config import config


# 全局线程池
thread_pool_executor = ThreadPoolExecutor(
    max_workers=config.thread_pool_max_workers, 
    thread_name_prefix="model_inference"
)


# 模型实例（全局加载）
sv_pipeline = None
model_asr = None
model_vad = None


def initialize_models():
    """初始化所有AI模型"""
    global sv_pipeline, model_asr, model_vad
    
    logger.info("开始加载AI模型...")
    
    # 加载说话人验证模型 (CAM++模型，更轻量且性能更优)
    sv_pipeline = pipeline(
        task='speaker-verification',
        model='iic/speech_campplus_sv_zh-cn_16k-common',
        model_revision='v1.0.0'
    )
    logger.info("说话人验证模型(CAM++)加载完成")
    
    # 加载语音识别模型 - 目前只有Small版本可用
    model_asr = AutoModel(
        model="iic/SenseVoiceSmall",
        trust_remote_code=True,
        remote_code="./model.py",
        device="cuda:0" if config.use_gpu else "cpu",
        disable_update=True
    )
    logger.info("语音识别模型(SenseVoiceSmall)加载完成")
    
    # 加载VAD模型
    model_vad = AutoModel(
        model="fsmn-vad",
        model_revision="v2.0.4",
        disable_pbar=True,
        max_end_silence_time=500,
        disable_update=True,
    )
    logger.info("VAD模型加载完成")
    
    logger.info("所有AI模型加载完成")


# 异步包装函数
async def async_vad_generate(chunk, cache_vad, chunk_size_ms):
    """异步VAD推理"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thread_pool_executor,
        lambda: model_vad.generate(
            input=chunk, 
            cache=cache_vad, 
            is_final=False, 
            chunk_size=chunk_size_ms
        )
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


async def asr_async(audio, lang, cache, use_itn=False):
    """异步语音识别函数（带计时）"""
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


@asynccontextmanager
async def model_service_lifespan(app):
    """模型服务生命周期管理"""
    # 应用启动
    logger.info("Model service starting up...")
    initialize_models()
    yield
    # 应用关闭
    logger.info("Model service shutting down...")
    thread_pool_executor.shutdown(wait=True)
    logger.info("Thread pool executor shut down") 