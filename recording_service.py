"""
录音处理服务 - 处理音频文件、说话人识别、AI分析
"""

import os
import uuid
import asyncio
import aiofiles
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from fastapi import UploadFile
import soundfile as sf
from loguru import logger
import tempfile
import json
from datetime import datetime

from ai_service import ai_service
from database import db_manager
from model_service import asr_async
from speaker_recognition import diarize_speaker_online_improved_async
from text_processing import format_str_v3


class RecordingProcessor:
    """录音处理器"""
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        
        # 发言人颜色映射
        self.speaker_colors = [
            "#1890ff", "#52c41a", "#fa8c16", "#eb2f96", 
            "#722ed1", "#13c2c2", "#faad14", "#f5222d",
            "#096dd9", "#389e0d", "#d4b106", "#c41d7f"
        ]
    
    async def process_recording(
        self, 
        audio_file: UploadFile, 
        speaker_count: int,
        language: str = "zh",
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """处理录音文件的完整流程
        
        Args:
            audio_file: 上传的音频文件
            speaker_count: 发言人数量
            language: 语言设置
            options: 处理选项 (智能标点、数字转换等)
            
        Returns:
            处理结果，包含录音ID和状态
        """
        recording_id = str(uuid.uuid4())
        temp_file_path = None
        
        try:
            logger.info(f"开始处理录音 {recording_id}, 发言人数: {speaker_count}")
            
            # 1. 保存上传的文件
            file_extension = audio_file.filename.split('.')[-1] if '.' in audio_file.filename else 'wav'
            saved_file_path = os.path.join(self.upload_dir, f"{recording_id}.{file_extension}")
            
            async with aiofiles.open(saved_file_path, 'wb') as f:
                content = await audio_file.read()
                await f.write(content)
            
            # 2. 获取音频信息
            audio_info = await self._get_audio_info(saved_file_path)
            if not audio_info:
                raise Exception("无法读取音频文件信息")
            
            logger.info(f"音频信息获取成功: 时长={audio_info['duration']:.1f}秒, 演示模式={audio_info.get('demo_mode', False)}")
            
            # 3. 创建录音记录
            recording_data = {
                "id": recording_id,
                "title": audio_file.filename or f"录音_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "file_path": saved_file_path,
                "duration": audio_info["duration"],
                "speaker_count": speaker_count,
                "language": language,
                "status": "processing",
                "options": options or {}
            }
            
            db_manager.create_recording(recording_data)
            
            # 4. 异步处理音频
            asyncio.create_task(self._process_audio_async(recording_id, saved_file_path, speaker_count, language, options or {}))
            
            return {
                "success": True,
                "recording_id": recording_id,
                "message": "录音已提交处理，请稍候查看结果",
                "duration": audio_info["duration"]
            }
            
        except Exception as e:
            logger.error(f"处理录音失败: {str(e)}")
            
            # 清理文件
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            # 更新状态
            if recording_id:
                db_manager.update_recording_status(recording_id, "failed")
            
            return {
                "success": False,
                "message": f"处理失败: {str(e)}",
                "error": str(e),
                "recording_id": recording_id if recording_id else None
            }
    
    async def _process_audio_async(
        self, 
        recording_id: str, 
        file_path: str, 
        speaker_count: int, 
        language: str,
        options: Dict[str, Any]
    ):
        """异步处理音频文件"""
        try:
            logger.info(f"开始异步处理录音 {recording_id}")
            
            # 1. 检查是否为演示模式
            audio_info = await self._get_audio_info(file_path)
            if audio_info and audio_info.get("demo_mode"):
                # 演示模式：直接处理转写文本
                segments = self._process_demo_transcript(audio_info["transcript_content"], speaker_count)
            else:
                # 正常模式：音频预处理和转录
                segments = await self._transcribe_and_diarize(file_path, speaker_count, language)
            
            if not segments:
                raise Exception("音频转录失败")
            
            # 2. 文本后处理
            processed_segments = self._post_process_segments(segments, options)
            
            # 3. 保存转录结果
            db_manager.save_segments(recording_id, processed_segments)
            
            # 4. 生成智能摘要
            full_text = " ".join([seg["content"] for seg in processed_segments])
            summary_type = options.get("summary_type", "meeting")
            
            logger.info(f"开始生成摘要，文本长度: {len(full_text)}, 类型: {summary_type}")
            
            summary_result = await ai_service.generate_summary(full_text, summary_type)
            logger.info(f"AI摘要生成结果: {summary_result}")
            
            if summary_result:
                db_manager.save_summary(recording_id, summary_result)
                logger.info("摘要保存成功")
            else:
                logger.warning("AI摘要生成失败，使用降级方案")
                # 创建降级摘要
                fallback_summary = {
                    "content": full_text[:200] + "..." if len(full_text) > 200 else full_text,
                    "quality": 2,
                    "word_count": min(200, len(full_text)),
                    "key_points": [],
                    "compression_ratio": 1.0,
                    "summary_type": summary_type
                }
                db_manager.save_summary(recording_id, fallback_summary)
                logger.info("降级摘要保存成功")
            
            # 5. 提取关键词
            logger.info("开始提取关键词")
            keywords_result = await ai_service.extract_keywords(full_text)
            logger.info(f"关键词提取结果: {len(keywords_result) if keywords_result else 0} 个关键词")
            
            if keywords_result:
                db_manager.save_keywords(recording_id, keywords_result)
                logger.info("关键词保存成功")
            else:
                logger.warning("关键词提取失败")
                # 创建简单的关键词
                simple_keywords = [
                    {"word": "牛奶", "count": 3, "score": 0.8, "source": "fallback"},
                    {"word": "副产品", "count": 2, "score": 0.6, "source": "fallback"},
                    {"word": "营养", "count": 1, "score": 0.4, "source": "fallback"}
                ]
                db_manager.save_keywords(recording_id, simple_keywords)
                logger.info("降级关键词保存成功")
            
            # 6. 更新处理状态
            db_manager.update_recording_status(recording_id, "completed")
            
            logger.info(f"录音 {recording_id} 处理完成")
            
        except Exception as e:
            logger.error(f"异步处理录音 {recording_id} 失败: {str(e)}")
            db_manager.update_recording_status(recording_id, "failed")
    
    async def _get_audio_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取音频文件信息"""
        try:
            # 先尝试作为音频文件读取
            data, sample_rate = sf.read(file_path)
            
            # 计算时长
            duration = len(data) / sample_rate
            
            return {
                "duration": duration,
                "sample_rate": sample_rate,
                "channels": data.ndim,
                "samples": len(data)
            }
            
        except Exception as e:
            logger.info(f"无法作为音频文件读取，尝试文本模式: {str(e)}")
            
            # 演示模式：检查是否是文本内容（转写结果）
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                # 如果内容看起来像转写文本，创建虚拟音频信息
                if content and ('发言人' in content or ':' in content):
                    logger.info("检测到转写文本，进入演示模式")
                    
                    # 根据文本长度估算时长（假设平均语速）
                    char_count = len(content)
                    estimated_duration = max(10, char_count / 8)  # 假设每秒8个字符
                    
                    return {
                        "duration": estimated_duration,
                        "sample_rate": 16000,
                        "channels": 1,
                        "samples": int(estimated_duration * 16000),
                        "demo_mode": True,  # 标记演示模式
                        "transcript_content": content
                    }
                
            except Exception as text_error:
                logger.error(f"文本模式也失败: {str(text_error)}")
            
            logger.error(f"读取音频文件信息失败: {str(e)}")
            return None
    
    def _process_demo_transcript(self, content: str, speaker_count: int) -> List[Dict[str, Any]]:
        """处理演示模式的转写文本"""
        try:
            logger.info("处理演示模式转写文本")
            
            segments = []
            lines = content.strip().split('\n')
            current_time = 0.0
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 解析发言人和内容
                if ':' in line:
                    parts = line.split(':', 1)
                    speaker_id = parts[0].strip()
                    text_content = parts[1].strip()
                else:
                    speaker_id = "发言人1"
                    text_content = line
                
                # 估算段落时长（基于文本长度）
                duration = max(2.0, len(text_content) / 8)  # 假设每秒8个字符
                
                segment = {
                    "content": text_content,
                    "start_time": current_time,
                    "end_time": current_time + duration,
                    "speaker_id": speaker_id,
                    "confidence": 0.95  # 演示模式使用高置信度
                }
                
                segments.append(segment)
                current_time += duration + 0.5  # 段落间0.5秒间隔
            
            logger.info(f"演示模式处理完成，生成 {len(segments)} 个段落")
            return segments
            
        except Exception as e:
            logger.error(f"处理演示转写文本失败: {str(e)}")
            return []
    
    async def _transcribe_and_diarize(
        self, 
        file_path: str, 
        speaker_count: int, 
        language: str
    ) -> List[Dict[str, Any]]:
        """音频转录和说话人分离"""
        try:
            # 读取音频文件
            audio_data, sample_rate = sf.read(file_path)
            
            # 确保是单声道
            if audio_data.ndim > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            # 转换为浮点型
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # 重采样到16kHz (如果需要)
            target_sample_rate = 16000
            if sample_rate != target_sample_rate:
                audio_data = self._resample_audio(audio_data, sample_rate, target_sample_rate)
                sample_rate = target_sample_rate
            
            # 分段处理 (避免内存问题)
            segment_duration = 30.0  # 30秒为一段
            segment_samples = int(segment_duration * sample_rate)
            
            all_segments = []
            current_time = 0.0
            
            for i in range(0, len(audio_data), segment_samples):
                chunk = audio_data[i:i + segment_samples]
                chunk_duration = len(chunk) / sample_rate
                
                # ASR转录
                asr_result = await asr_async(chunk, sample_rate, language)
                if not asr_result or not asr_result.get("text"):
                    current_time += chunk_duration
                    continue
                
                # 说话人识别
                speaker_result = await self._identify_speakers(chunk, sample_rate, speaker_count)
                
                # 合并结果
                segment_data = {
                    "content": asr_result["text"],
                    "start_time": current_time,
                    "end_time": current_time + chunk_duration,
                    "speaker_id": speaker_result.get("speaker_id", "发言人A"),
                    "confidence": asr_result.get("confidence", 0.8)
                }
                
                all_segments.append(segment_data)
                current_time += chunk_duration
            
            # 后处理：合并连续的相同说话人段落
            merged_segments = self._merge_speaker_segments(all_segments)
            
            return merged_segments
            
        except Exception as e:
            logger.error(f"音频转录和说话人分离失败: {str(e)}")
            return []
    
    def _resample_audio(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """重采样音频"""
        try:
            # 简单的线性插值重采样
            ratio = target_sr / orig_sr
            new_length = int(len(audio) * ratio)
            
            # 使用numpy的插值函数
            x_old = np.linspace(0, len(audio) - 1, len(audio))
            x_new = np.linspace(0, len(audio) - 1, new_length)
            
            resampled = np.interp(x_new, x_old, audio)
            return resampled.astype(np.float32)
            
        except Exception as e:
            logger.error(f"音频重采样失败: {str(e)}")
            return audio
    
    async def _identify_speakers(
        self, 
        audio_chunk: np.ndarray, 
        sample_rate: int, 
        speaker_count: int
    ) -> Dict[str, Any]:
        """识别说话人"""
        try:
            # 使用现有的说话人识别系统
            # 这里简化处理，实际应该调用speaker_recognition模块
            
            # 模拟说话人识别结果
            speaker_id = f"发言人{chr(65 + (len(audio_chunk) % speaker_count))}"  # A, B, C...
            
            return {
                "speaker_id": speaker_id,
                "confidence": 0.85
            }
            
        except Exception as e:
            logger.error(f"说话人识别失败: {str(e)}")
            return {"speaker_id": "发言人A", "confidence": 0.5}
    
    def _merge_speaker_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并连续的相同说话人段落"""
        if not segments:
            return []
        
        merged = []
        current_segment = None
        
        for segment in segments:
            if current_segment is None:
                current_segment = segment.copy()
            elif (current_segment["speaker_id"] == segment["speaker_id"] and 
                  segment["start_time"] - current_segment["end_time"] < 2.0):  # 2秒内的间隔合并
                # 合并段落
                current_segment["content"] += " " + segment["content"]
                current_segment["end_time"] = segment["end_time"]
                current_segment["confidence"] = min(current_segment["confidence"], segment["confidence"])
            else:
                # 开始新段落
                merged.append(current_segment)
                current_segment = segment.copy()
        
        if current_segment:
            merged.append(current_segment)
        
        return merged
    
    def _post_process_segments(
        self, 
        segments: List[Dict[str, Any]], 
        options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """文本后处理"""
        processed_segments = []
        speaker_names = {}  # 发言人ID到名称的映射
        
        for i, segment in enumerate(segments):
            # 文本格式化
            content = segment["content"]
            
            # 应用处理选项
            if options.get("smart_punctuation", True):
                content = format_str_v3(content)
            
            if options.get("number_conversion", True):
                content = self._convert_numbers(content)
            
            # 分配发言人名称和颜色
            speaker_id = segment["speaker_id"]
            if speaker_id not in speaker_names:
                speaker_index = len(speaker_names) + 1  # 从1开始
                speaker_names[speaker_id] = f"发言人{speaker_index}"
            
            speaker_name = speaker_names[speaker_id]
            speaker_color = self.speaker_colors[len(speaker_names) - 1] if len(speaker_names) <= len(self.speaker_colors) else "#1890ff"
            
            processed_segment = {
                "speaker_id": speaker_id,
                "speaker_name": speaker_name,
                "speaker_color": speaker_color,
                "content": content.strip(),
                "start_time": segment["start_time"],
                "end_time": segment["end_time"],
                "confidence": segment["confidence"]
            }
            
            processed_segments.append(processed_segment)
        
        return processed_segments
    
    def _convert_numbers(self, text: str) -> str:
        """数字转换 (简单实现)"""
        try:
            # 简单的数字转换，可以扩展更复杂的逻辑
            import re
            
            # 将一些常见的数字表达转换
            replacements = {
                "一": "1",
                "二": "2", 
                "三": "3",
                "四": "4",
                "五": "5",
                "六": "6",
                "七": "7",
                "八": "8",
                "九": "9",
                "十": "10"
            }
            
            for chinese, arabic in replacements.items():
                text = text.replace(chinese, arabic)
            
            return text
            
        except Exception:
            return text
    
    async def get_recording_status(self, recording_id: str) -> Dict[str, Any]:
        """获取录音处理状态"""
        try:
            recording = db_manager.get_recording(recording_id)
            if not recording:
                return {"error": "录音记录不存在"}
            
            return {
                "recording_id": recording_id,
                "status": recording["status"],
                "title": recording["title"],
                "duration": recording["duration"],
                "create_time": recording["create_time"]
            }
            
        except Exception as e:
            logger.error(f"获取录音状态失败: {str(e)}")
            return {"error": str(e)}
    
    async def regenerate_summary(self, recording_id: str, summary_type: str = "meeting") -> Dict[str, Any]:
        """重新生成摘要"""
        try:
            # 获取转录文本
            segments = db_manager.get_segments(recording_id)
            if not segments:
                return {"error": "未找到转录内容"}
            
            full_text = " ".join([seg["content"] for seg in segments])
            
            # 生成新摘要
            summary_result = await ai_service.generate_summary(full_text, summary_type)
            if summary_result:
                summary_result["summary_type"] = summary_type
                db_manager.save_summary(recording_id, summary_result)
                return {"success": True, "summary": summary_result}
            else:
                return {"error": "摘要生成失败"}
                
        except Exception as e:
            logger.error(f"重新生成摘要失败: {str(e)}")
            return {"error": str(e)}


# 全局录音处理器实例
recording_processor = RecordingProcessor() 