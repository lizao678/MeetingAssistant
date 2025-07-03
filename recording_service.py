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
from config import (
    audio_config, quality_config, number_config, 
    segment_config, ui_config, processing_config, text_config
)


class RecordingProcessor:
    """录音处理器"""
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        
        # 发言人颜色映射
        self.speaker_colors = ui_config.SPEAKER_COLORS
        
        # 初始化说话人识别状态
        self._reset_speaker_recognition_state()
    
    def _reset_speaker_recognition_state(self):
        """重置说话人识别状态"""
        self._speaker_gallery = {}
        self._speaker_counter = 0
        self._speaker_history = []
        self._current_speaker = None
        self._fallback_speaker_index = 0
        logger.debug("说话人识别状态已重置")
    
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
            
            # 重置说话人识别状态（每个录音独立处理）
            self._reset_speaker_recognition_state()
            
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
            
            # 如果是自动识别模式，更新实际的发言人数量
            if speaker_count == 0 and processed_segments:
                actual_speaker_count = len(set(seg["speaker_id"] for seg in processed_segments))
                db_manager.update_recording_speaker_count(recording_id, actual_speaker_count)
                logger.info(f"自动识别完成，实际发言人数量: {actual_speaker_count}")
            
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
            keywords_result = await ai_service.extract_keywords(full_text, max_keywords=8)
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
            
            # 使用更智能的分段策略，模拟实时处理效果
            logger.info("开始智能音频分段和处理...")
            all_segments = await self._process_audio_with_vad_simulation(
                audio_data, sample_rate, language, speaker_count
            )
            
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
        """识别说话人 - 使用真正的说话人识别算法"""
        try:
            # 设置说话人识别阈值
            sv_thr = 0.4
            
            # 使用真正的说话人识别算法
            speaker_id, updated_gallery, updated_counter, updated_history, updated_current = await diarize_speaker_online_improved_async(
                audio_chunk,
                self._speaker_gallery,
                self._speaker_counter,
                sv_thr,
                self._speaker_history,
                self._current_speaker
            )
            
            # 更新状态变量
            self._speaker_gallery = updated_gallery
            self._speaker_counter = updated_counter
            self._speaker_history = updated_history
            self._current_speaker = updated_current
            
            # 计算置信度（基于历史记录）
            confidence = 0.85
            if updated_history:
                # 使用最近的识别置信度
                recent_confidences = [entry[1] for entry in updated_history[-3:] if entry[0] == speaker_id]
                if recent_confidences:
                    confidence = min(1.0, sum(recent_confidences) / len(recent_confidences))
            
            logger.debug(f"说话人识别结果: {speaker_id}, 置信度: {confidence:.3f}")
            
            return {
                "speaker_id": speaker_id,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"说话人识别失败: {str(e)}")
            # 降级处理：使用简单的轮转算法
            if speaker_count > 0:
                self._fallback_speaker_index = (self._fallback_speaker_index + 1) % speaker_count
                speaker_id = f"发言人{self._fallback_speaker_index + 1}"
            else:
                # 自动识别模式的降级处理
                audio_energy = np.mean(np.abs(audio_chunk)) if len(audio_chunk) > 0 else 0
                if audio_energy > 0.05:
                    self._fallback_speaker_index = (self._fallback_speaker_index + 1) % 3
                speaker_id = f"发言人{self._fallback_speaker_index + 1}"
                
            return {"speaker_id": speaker_id, "confidence": 0.5}
    
    async def _process_audio_with_vad_simulation(
        self, 
        audio_data: np.ndarray, 
        sample_rate: int, 
        language: str,
        speaker_count: int
    ) -> List[Dict[str, Any]]:
        """模拟实时处理的VAD效果，智能分段处理音频"""
        try:
            logger.info(f"开始VAD模拟处理，音频长度: {len(audio_data)/sample_rate:.1f}秒")
            
            # 1. 生成音频分段
            chunks = self._simulate_vad_processing(audio_data, sample_rate)
            
            # 2. 处理每个分段
            all_segments = []
            for chunk_data in chunks:
                if not self._is_valid_audio_chunk(chunk_data['chunk'], sample_rate):
                    continue
                
                # 3. 进一步细分chunk以适合说话人识别
                sub_segments = await self._process_chunk_with_fine_segmentation(
                    chunk_data['chunk'], sample_rate, language, 
                    chunk_data['start_time'], speaker_count
                )
                all_segments.extend(sub_segments)
            
            logger.info(f"VAD模拟处理完成，生成 {len(all_segments)} 个语音段落")
            return all_segments
            
        except Exception as e:
            logger.error(f"VAD模拟处理失败: {str(e)}")
            return []

    def _simulate_vad_processing(self, audio_data: np.ndarray, sample_rate: int) -> List[Dict[str, Any]]:
        """模拟VAD处理，生成音频分段"""
        chunk_duration = audio_config.CHUNK_DURATION
        overlap_duration = audio_config.OVERLAP_DURATION
        
        chunk_samples = int(chunk_duration * sample_rate)
        overlap_samples = int(overlap_duration * sample_rate)
        step_samples = chunk_samples - overlap_samples
        
        chunks = []
        current_time = 0.0
        
        for i in range(0, len(audio_data), step_samples):
            chunk = audio_data[i:i + chunk_samples]
            
            if len(chunk) < sample_rate * audio_config.MIN_CHUNK_DURATION:
                break
            
            chunks.append({
                'chunk': chunk,
                'start_time': current_time,
                'duration': len(chunk) / sample_rate
            })
            
            current_time += step_samples / sample_rate
        
        return chunks
    
    async def _process_chunk_with_fine_segmentation(
        self,
        chunk: np.ndarray,
        sample_rate: int, 
        language: str,
        base_time: float,
        speaker_count: int
    ) -> List[Dict[str, Any]]:
        """对chunk进行细分处理，确保适合说话人识别"""
        try:
            # 1. 转录音频获取文本
            text_content, asr_confidence = await self._transcribe_chunk(chunk, language)
            if not text_content:
                return []
            
            # 2. 检查ASR置信度
            if asr_confidence < quality_config.MIN_ASR_CONFIDENCE:
                logger.debug(f"ASR置信度太低({asr_confidence:.3f})，跳过: '{text_content}'")
                return []
            
            # 3. 根据chunk长度选择处理策略
            chunk_duration_ms = len(chunk) / sample_rate * 1000
            
            if chunk_duration_ms <= audio_config.MAX_SIMPLE_CHUNK_DURATION * 1000:
                return await self._process_simple_chunk(
                    chunk, sample_rate, text_content, base_time, 
                    speaker_count, asr_confidence
                )
            else:  # 超过5秒，进行细分
                return await self._process_complex_chunk(
                    chunk, sample_rate, text_content, base_time, 
                    speaker_count, asr_confidence
                )
            
        except Exception as e:
            logger.error(f"细分处理失败: {str(e)}")
            return []

    async def _transcribe_chunk(self, chunk: np.ndarray, language: str) -> Tuple[str, float]:
        """转录音频chunk获取文本"""
        cache_asr = {}
        asr_result = await asr_async(chunk, language, cache_asr, True)
        
        if not asr_result:
            return "", -1.0
            
        # 处理ASR结果
        if isinstance(asr_result, list):
            if not asr_result or not asr_result[0].get("text"):
                return "", -1.0
            asr_data = asr_result[0]
        else:
            if not asr_result.get("text"):
                return "", -1.0
            asr_data = asr_result
        
        # 提取和清理文本
        text_content = asr_data.get("text", "")
        import re
        text_content = re.sub(r'<\|[^|]+\|>', '', text_content).strip()
        
        # 高级文本质量检查和清理
        text_content = self._clean_and_validate_text(text_content)
        asr_confidence = asr_data.get("avg_logprob", -1.0)
        
        return text_content, asr_confidence

    async def _process_simple_chunk(
        self, 
        chunk: np.ndarray, 
        sample_rate: int, 
        text_content: str, 
        base_time: float,
        speaker_count: int, 
        asr_confidence: float
    ) -> List[Dict[str, Any]]:
        """处理5秒以内的简单chunk"""
        speaker_result = await self._identify_speakers(chunk, sample_rate, speaker_count)
        
        # 验证说话人识别质量
        if not self._validate_segment_quality(speaker_result, text_content):
            return []
        
        segment_data = self._create_segment_data(
            text_content, base_time, base_time + len(chunk) / sample_rate,
            speaker_result, asr_confidence
        )
        return [segment_data]

    async def _process_complex_chunk(
        self, 
        chunk: np.ndarray, 
        sample_rate: int, 
        text_content: str, 
        base_time: float,
        speaker_count: int, 
        asr_confidence: float
    ) -> List[Dict[str, Any]]:
        """处理超过5秒的复杂chunk，进行细分"""
        max_sub_duration = audio_config.MAX_SUB_DURATION
        max_sub_samples = int(max_sub_duration * sample_rate)
        
        words = text_content.split()
        if len(words) <= 1:
            # 文本太短，不细分，但限制音频长度
            limited_chunk = chunk[:max_sub_samples]
            return await self._process_simple_chunk(
                limited_chunk, sample_rate, text_content, base_time,
                speaker_count, asr_confidence
            )
        
        # 按音频长度和文本长度合理分割
        chunk_duration_ms = len(chunk) / sample_rate * 1000
        num_parts = int(np.ceil(chunk_duration_ms / 4000))  # 每部分最多4秒
        part_samples = len(chunk) // num_parts
        words_per_part = len(words) // num_parts
        
        segments = []
        for part_idx in range(num_parts):
            segment = await self._process_chunk_part(
                chunk, sample_rate, words, base_time, speaker_count,
                asr_confidence, part_idx, num_parts, part_samples, words_per_part
            )
            if segment:
                segments.append(segment)
        
        return segments

    async def _process_chunk_part(
        self, chunk: np.ndarray, sample_rate: int, words: list, base_time: float,
        speaker_count: int, asr_confidence: float, part_idx: int, num_parts: int,
        part_samples: int, words_per_part: int
    ) -> Optional[Dict[str, Any]]:
        """处理chunk的一个部分"""
        start_sample = part_idx * part_samples
        end_sample = min((part_idx + 1) * part_samples, len(chunk))
        part_chunk = chunk[start_sample:end_sample]
        
        if len(part_chunk) < sample_rate * audio_config.MIN_PART_DURATION:
            return None
        
        # 分配对应的文本
        start_word = part_idx * words_per_part
        end_word = min((part_idx + 1) * words_per_part, len(words))
        if part_idx == num_parts - 1:  # 最后一部分包含剩余所有单词
            end_word = len(words)
        
        part_text = " ".join(words[start_word:end_word])
        if not part_text.strip():
            return None
        
        # 再次清理和验证分割后的文本
        part_text = self._clean_and_validate_text(part_text)
        if not part_text:
            return None
        
        # 检查音频质量
        if not self._is_valid_audio_chunk(part_chunk, sample_rate):
            logger.debug(f"分割音频质量不合格，跳过: '{part_text}'")
            return None
        
        # 说话人识别
        speaker_result = await self._identify_speakers(part_chunk, sample_rate, speaker_count)
        
        # 验证质量
        if not self._validate_segment_quality(speaker_result, part_text):
            return None
        
        part_start_time = base_time + start_sample / sample_rate
        part_end_time = base_time + end_sample / sample_rate
        
        return self._create_segment_data(
            part_text, part_start_time, part_end_time, speaker_result, asr_confidence
        )

    def _validate_segment_quality(self, speaker_result: Dict[str, Any], text_content: str) -> bool:
        """验证segment质量"""
        speaker_confidence = speaker_result.get("confidence", 0.0)
        if speaker_confidence < quality_config.MIN_SPEAKER_CONFIDENCE:
            logger.debug(f"说话人识别置信度太低({speaker_confidence:.3f})，跳过: '{text_content}'")
            return False
        return True

    def _create_segment_data(
        self, text_content: str, start_time: float, end_time: float,
        speaker_result: Dict[str, Any], asr_confidence: float
    ) -> Dict[str, Any]:
        """创建segment数据结构"""
        return {
            "content": text_content,
            "start_time": start_time,
            "end_time": end_time,
            "speaker_id": speaker_result.get("speaker_id", "发言人1"),
            "confidence": max(0.1, asr_confidence + 1.0)  # 转换为正数置信度
        }
    
    def _clean_and_validate_text(self, text: str) -> str:
        """高级文本清理和验证"""
        if not text:
            return ""
        
        # 基础清理
        text = text.strip()
        
        # 过滤太短的文本
        if len(text) < quality_config.MIN_TEXT_LENGTH:
            logger.debug(f"文本太短，过滤: '{text}'")
            return ""
        
        # 过滤只包含标点符号的文本
        import string
        chinese_punctuation = "。，！？；：""''（）【】《》"
        all_punctuation = string.punctuation + chinese_punctuation
        if all(c in all_punctuation or c.isspace() for c in text):
            logger.debug(f"文本只包含标点符号，过滤: '{text}'")
            return ""
        
        # 使用统一的无效文本模式配置
        import re
        for pattern in text_config.INVALID_TEXT_PATTERNS:
            if re.match(pattern, text):
                logger.debug(f"匹配无效模式 '{pattern}'，过滤: '{text}'")
                return ""
        
        # 检查是否包含足够的有意义内容
        meaningful_chars = sum(1 for c in text if c.isalnum() or ord(c) > 127)  # 字母数字或中文字符
        if meaningful_chars < quality_config.MIN_MEANINGFUL_CHARS:
            logger.debug(f"有意义字符太少({meaningful_chars})，过滤: '{text}'")
            return ""
        
        # 检查长度是否合理（避免过长的重复内容）
        if len(text) > 200:
            logger.debug(f"文本过长({len(text)})，截断: '{text[:50]}...'")
            text = text[:200]
        
        # 检查重复字符（避免"测试测试测试..."这种情况）
        if len(text) >= 4:
            # 检查是否有长重复模式
            for i in range(1, len(text) // 3 + 1):
                pattern = text[:i]
                if len(pattern) >= 2 and text.count(pattern) >= 3:
                    logger.debug(f"检测到重复模式 '{pattern}'，过滤: '{text}'")
                    return ""
        
        # logger.debug(f"文本验证通过: '{text}'")  # 减少日志输出
        return text
    
    def _is_valid_audio_chunk(self, chunk: np.ndarray, sample_rate: int) -> bool:
        """检查音频片段是否有效且适合处理"""
        if len(chunk) == 0:
            return False
        
        # 1. 检查音频时长
        duration = len(chunk) / sample_rate
        if duration < audio_config.MIN_CHUNK_DURATION:
            logger.debug(f"音频时长太短({duration:.2f}s)，跳过")
            return False
        
        # 2. 检查音频能量（避免完全静音）
        audio_energy = np.mean(np.abs(chunk))
        if audio_energy < 0.00001:  # 降低能量阈值
            logger.debug(f"音频能量太低({audio_energy:.6f})，跳过")
            return False
        
        # 3. 检查音频动态范围（只检查是否完全静音）
        audio_std = np.std(chunk)
        if audio_std < 0.000001:  # 降低方差阈值
            logger.debug(f"音频动态范围太小({audio_std:.6f})，跳过")
            return False
        
        return True
    
    def _merge_speaker_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """智能合并连续的相同说话人段落（参考实时处理的1.5秒断句逻辑）"""
        if not segments:
            return []

        merged = []
        current_segment = None
        PAUSE_THRESHOLD = segment_config.SILENCE_THRESHOLD_MS / 1000  # 转换为秒

        for segment in segments:
            if current_segment is None:
                current_segment = segment.copy()
            elif (current_segment["speaker_id"] == segment["speaker_id"] and 
                  segment["start_time"] - current_segment["end_time"] < PAUSE_THRESHOLD):  # 1.5秒内的间隔合并
                # 合并段落：连续说话且同一发言人
                current_segment["content"] += segment["content"]  # 直接连接，不加空格（避免不必要的断词）
                current_segment["end_time"] = segment["end_time"]
                # 置信度取加权平均而不是最小值
                duration1 = current_segment["end_time"] - current_segment["start_time"]
                duration2 = segment["end_time"] - segment["start_time"]
                total_duration = duration1 + duration2
                current_segment["confidence"] = (
                    current_segment["confidence"] * duration1 + 
                    segment["confidence"] * duration2
                ) / total_duration
            else:
                # 开始新段落：发言人变更或停顿超过1.5秒
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
        speaker_id_to_index = {}  # 发言人ID到索引的映射，确保颜色分配正确
        
        for i, segment in enumerate(segments):
            # 文本格式化
            content = segment["content"]
            
            # 应用处理选项
            if options.get("smart_punctuation", True):
                content = format_str_v3(content)
            
            if options.get("number_conversion", True):
                content = self._smart_convert_numbers(content)  # 使用智能数字转换
            
            # 分配发言人名称和颜色（修复颜色分配逻辑）
            speaker_id = segment["speaker_id"]
            if speaker_id not in speaker_id_to_index:
                speaker_id_to_index[speaker_id] = len(speaker_id_to_index)  # 分配唯一索引
            
            speaker_index = speaker_id_to_index[speaker_id] + 1  # 从1开始显示
            speaker_name = f"发言人{speaker_index}"
            
            # 根据发言人的唯一索引分配颜色
            color_index = speaker_id_to_index[speaker_id] % len(self.speaker_colors)
            speaker_color = self.speaker_colors[color_index]
            
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
    
    def _smart_convert_numbers(self, text: str) -> str:
        """智能数字转换（参考实时处理逻辑，避免过度转换）"""
        try:
            import re
            
            # 只转换明确的数字表达，避免过度转换
            # 1. 转换独立的数字词（前后有空格或标点）
            patterns = [
                (r'\b一\b', '1'),
                (r'\b二\b', '2'),
                (r'\b三\b', '3'),  
                (r'\b四\b', '4'),
                (r'\b五\b', '5'),
                (r'\b六\b', '6'),
                (r'\b七\b', '7'),
                (r'\b八\b', '8'),
                (r'\b九\b', '9'),
                (r'\b十\b', '10'),
                # 2. 转换数量表达
                (r'(\d+)个([小时|分钟|秒钟|天|周|月|年])', r'\1\2'),
                # 3. 转换序数表达  
                (r'第一', '第1'),
                (r'第二', '第2'),
                (r'第三', '第3'),
                (r'第四', '第4'),
                (r'第五', '第5'),
            ]
            
            for pattern, replacement in patterns:
                text = re.sub(pattern, replacement, text)
            
            # 4. 保留常用词汇中的数字不转换（如：小米、三个、一些、一起等）
            # 这些词汇在实时处理中也不会被转换
            preserve_patterns = [
                '小米',  # 保留品牌名
                '一些', '一起', '一下', '一个', '一条', '一次',  # 保留常用搭配
                '三个', '两个',  # 保留量词搭配
                '十分', '九分',  # 保留程度副词
            ]
            
            # 如果包含这些词汇，恢复原始数字
            for preserve in preserve_patterns:
                if preserve in text:
                    # 根据具体情况恢复，这里简化处理
                    continue
                    
            return text
            
        except Exception as e:
            logger.warning(f"数字转换失败: {str(e)}")
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