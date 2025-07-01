import os
import asyncio
import logging
import numpy as np
import soundfile as sf
from typing import List, Dict, Any, Optional
from datetime import datetime
import tempfile
import subprocess

# 音频处理
import librosa
from pyannote.audio import Pipeline
import whisper

# 数据库
from database import db_manager

# 日志
logger = logging.getLogger(__name__)

class OfflineAudioProcessor:
    """离线音频处理器 - 使用更精确的模型重新识别"""
    
    def __init__(self):
        self.whisper_model = None
        self.diarization_pipeline = None
        self.sample_rate = 16000
        self.models_loaded = False
        self._initialization_lock = asyncio.Lock() if hasattr(asyncio, '_get_running_loop') and asyncio._get_running_loop() else None
    
    async def _ensure_models_loaded(self):
        """确保模型已加载"""
        if self.models_loaded:
            return
            
        # 如果没有锁，创建一个
        if self._initialization_lock is None:
            self._initialization_lock = asyncio.Lock()
            
        async with self._initialization_lock:
            # 双重检查
            if not self.models_loaded:
                await self._initialize_models()
                self.models_loaded = True

    async def _initialize_models(self):
        """初始化离线处理模型"""
        try:
            logger.info("开始加载离线处理模型...")
            
            # 1. 加载Whisper模型（中文效果很好）
            logger.info("加载Whisper模型...")
            self.whisper_model = whisper.load_model("medium")  # base/small/medium/large
            logger.info("Whisper模型加载完成")
            
            # 2. 加载pyannote说话人分离模型
            try:
                logger.info("加载pyannote说话人分离模型...")
                # 需要在HuggingFace注册并获取token
                # 这里使用免费的预训练模型
                self.diarization_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization@2.1",
                    use_auth_token=None  # 可以设置HuggingFace token
                )
                logger.info("pyannote模型加载完成")
            except Exception as e:
                logger.warning(f"pyannote模型加载失败，将使用简化的说话人分离: {e}")
                self.diarization_pipeline = None
            
            logger.info("所有离线处理模型加载完成")
            
        except Exception as e:
            logger.error(f"离线处理模型加载失败: {e}")
            # 即使失败也标记为已加载，避免重复尝试
            self.models_loaded = True
    
    async def reprocess_recording(self, recording_id: str) -> Dict[str, Any]:
        """重新处理录音（离线高精度）"""
        try:
            logger.info(f"开始离线重新处理录音: {recording_id}")
            
            # 0. 确保模型已初始化
            await self._ensure_models_loaded()
            
            # 1. 获取录音信息
            recording = db_manager.get_recording(recording_id)
            if not recording:
                return {"success": False, "error": "录音记录不存在"}
            
            file_path = recording.get("filePath")
            if not file_path or not os.path.exists(file_path):
                return {"success": False, "error": "录音文件不存在"}
            
            # 2. 预处理音频
            audio_data = await self._preprocess_audio(file_path)
            if audio_data is None:
                return {"success": False, "error": "音频预处理失败"}
            
            # 3. 离线语音识别（更准确）
            logger.info("开始离线语音识别...")
            transcription_result = await self._offline_transcribe(audio_data, file_path)
            
            # 4. 离线说话人分离（更准确）
            logger.info("开始离线说话人分离...")
            speaker_segments = await self._offline_speaker_diarization(
                audio_data, file_path, transcription_result
            )
            
            # 5. 合并转写和说话人信息
            final_segments = self._merge_transcription_and_speakers(
                transcription_result, speaker_segments
            )
            
            # 6. 后处理和保存
            processed_segments = self._post_process_offline_segments(
                final_segments, recording.get("options", {})
            )
            
            # 7. 更新数据库
            await self._update_recording_with_offline_results(
                recording_id, processed_segments, transcription_result
            )
            
            logger.info(f"录音 {recording_id} 离线重新处理完成")
            
            return {
                "success": True,
                "message": "离线重新处理完成",
                "segments_count": len(processed_segments),
                "processing_info": {
                    "used_whisper": self.whisper_model is not None,
                    "used_pyannote": self.diarization_pipeline is not None,
                    "total_duration": transcription_result.get("duration", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"离线重新处理录音失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _preprocess_audio(self, file_path: str) -> Optional[np.ndarray]:
        """预处理音频文件"""
        try:
            # 使用librosa加载音频，自动转换为目标采样率
            audio_data, sr = librosa.load(file_path, sr=self.sample_rate, mono=True)
            
            # 音频标准化
            audio_data = librosa.util.normalize(audio_data)
            
            logger.info(f"音频预处理完成: 时长={len(audio_data)/sr:.2f}秒, 采样率={sr}")
            return audio_data
            
        except Exception as e:
            logger.error(f"音频预处理失败: {e}")
            return None
    
    async def _offline_transcribe(self, audio_data: np.ndarray, file_path: str) -> Dict[str, Any]:
        """离线语音识别"""
        try:
            if self.whisper_model is None:
                # 降级方案：使用现有的SenseVoice
                return await self._fallback_transcribe(file_path)
            
            # 使用Whisper进行转写
            logger.info("使用Whisper进行离线转写...")
            
            # Whisper需要音频文件路径
            result = await asyncio.to_thread(
                self.whisper_model.transcribe,
                file_path,
                language='zh',  # 指定中文
                task='transcribe',
                word_timestamps=True,  # 获取词级时间戳
                initial_prompt="以下是中文语音对话内容。"  # 中文提示
            )
            
            # 处理结果
            segments = []
            for segment in result["segments"]:
                segments.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip(),
                    "confidence": 0.9,  # Whisper置信度较高
                    "words": segment.get("words", [])
                })
            
            return {
                "segments": segments,
                "language": result.get("language", "zh"),
                "duration": audio_data.shape[0] / self.sample_rate,
                "full_text": result["text"]
            }
            
        except Exception as e:
            logger.error(f"Whisper转写失败: {e}")
            return await self._fallback_transcribe(file_path)
    
    async def _offline_speaker_diarization(
        self, 
        audio_data: np.ndarray, 
        file_path: str,
        transcription_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """离线说话人分离"""
        try:
            if self.diarization_pipeline is None:
                # 降级方案：基于停顿和音频特征的简单分离
                return await self._fallback_speaker_diarization(
                    audio_data, transcription_result
                )
            
            logger.info("使用pyannote进行离线说话人分离...")
            
            # 使用pyannote进行说话人分离
            diarization = await asyncio.to_thread(
                self.diarization_pipeline, file_path
            )
            
            # 处理分离结果
            speaker_segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speaker_segments.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker,
                    "confidence": 0.85
                })
            
            logger.info(f"说话人分离完成，检测到 {len(set(seg['speaker'] for seg in speaker_segments))} 个说话人")
            
            return speaker_segments
            
        except Exception as e:
            logger.error(f"pyannote说话人分离失败: {e}")
            return await self._fallback_speaker_diarization(audio_data, transcription_result)
    
    async def _fallback_transcribe(self, file_path: str) -> Dict[str, Any]:
        """降级转写方案"""
        try:
            # 可以调用现有的SenseVoice或其他ASR
            logger.info("使用降级转写方案...")
            
            # 简化实现：返回基本结构
            audio_data, sr = sf.read(file_path)
            duration = len(audio_data) / sr
            
            return {
                "segments": [{
                    "start": 0.0,
                    "end": duration,
                    "text": "降级转写：请使用更好的ASR模型",
                    "confidence": 0.5
                }],
                "language": "zh",
                "duration": duration,
                "full_text": "降级转写：请使用更好的ASR模型",
                "fallback": True
            }
            
        except Exception as e:
            logger.error(f"降级转写失败: {e}")
            return {"segments": [], "language": "zh", "duration": 0, "full_text": ""}
    
    async def _fallback_speaker_diarization(
        self, 
        audio_data: np.ndarray, 
        transcription_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """降级说话人分离方案"""
        try:
            logger.info("使用降级说话人分离方案...")
            
            # 基于停顿检测的简单说话人分离
            segments = transcription_result.get("segments", [])
            speaker_segments = []
            
            current_speaker = "SPEAKER_00"
            speaker_count = 0
            
            for i, segment in enumerate(segments):
                # 简单规则：如果停顿超过2秒，可能是新说话人
                if i > 0:
                    prev_end = segments[i-1]["end"]
                    current_start = segment["start"]
                    
                    if current_start - prev_end > 2.0:  # 2秒停顿
                        speaker_count = (speaker_count + 1) % 3  # 最多3个说话人
                        current_speaker = f"SPEAKER_{speaker_count:02d}"
                
                speaker_segments.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "speaker": current_speaker,
                    "confidence": 0.6
                })
            
            return speaker_segments
            
        except Exception as e:
            logger.error(f"降级说话人分离失败: {e}")
            return []
    
    def _merge_transcription_and_speakers(
        self, 
        transcription_result: Dict[str, Any],
        speaker_segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """合并转写和说话人信息"""
        try:
            transcription_segments = transcription_result.get("segments", [])
            
            if not speaker_segments:
                # 如果没有说话人信息，使用默认说话人
                for segment in transcription_segments:
                    segment["speaker"] = "SPEAKER_00"
                return transcription_segments
            
            # 为每个转写段落匹配说话人
            merged_segments = []
            
            for trans_seg in transcription_segments:
                trans_start = trans_seg["start"]
                trans_end = trans_seg["end"]
                trans_mid = (trans_start + trans_end) / 2
                
                # 找到时间重叠最大的说话人段落
                best_speaker = "SPEAKER_00"
                max_overlap = 0
                
                for spk_seg in speaker_segments:
                    spk_start = spk_seg["start"]
                    spk_end = spk_seg["end"]
                    
                    # 计算重叠时间
                    overlap_start = max(trans_start, spk_start)
                    overlap_end = min(trans_end, spk_end)
                    overlap = max(0, overlap_end - overlap_start)
                    
                    if overlap > max_overlap:
                        max_overlap = overlap
                        best_speaker = spk_seg["speaker"]
                
                # 创建合并后的段落
                merged_segment = {
                    "start": trans_start,
                    "end": trans_end,
                    "text": trans_seg["text"],
                    "speaker": best_speaker,
                    "confidence": trans_seg.get("confidence", 0.8),
                    "words": trans_seg.get("words", [])
                }
                
                merged_segments.append(merged_segment)
            
            return merged_segments
            
        except Exception as e:
            logger.error(f"合并转写和说话人信息失败: {e}")
            return transcription_result.get("segments", [])
    
    def _post_process_offline_segments(
        self, 
        segments: List[Dict[str, Any]],
        options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """后处理离线段落"""
        try:
            processed_segments = []
            speaker_names = {}
            speaker_colors = ["#1890ff", "#52c41a", "#fa8c16", "#eb2f96", "#722ed1"]
            
            for segment in segments:
                # 分配说话人名称和颜色
                speaker_id = segment["speaker"]
                if speaker_id not in speaker_names:
                    speaker_index = len(speaker_names) + 1
                    speaker_names[speaker_id] = f"发言人{speaker_index}"
                
                speaker_name = speaker_names[speaker_id]
                color_index = (len(speaker_names) - 1) % len(speaker_colors)
                speaker_color = speaker_colors[color_index]
                
                # 文本后处理
                content = segment["text"].strip()
                
                # 应用处理选项
                if options.get("smart_punctuation", True):
                    content = self._add_smart_punctuation(content)
                
                if options.get("number_conversion", True):
                    content = self._convert_numbers(content)
                
                processed_segment = {
                    "speakerId": speaker_id,
                    "speakerName": speaker_name,
                    "speakerColor": speaker_color,
                    "content": content,
                    "startTime": segment["start"],
                    "endTime": segment["end"],
                    "confidence": segment["confidence"],
                    "offline_processed": True  # 标记为离线处理
                }
                
                processed_segments.append(processed_segment)
            
            return processed_segments
            
        except Exception as e:
            logger.error(f"后处理离线段落失败: {e}")
            return []
    
    def _add_smart_punctuation(self, text: str) -> str:
        """智能标点符号"""
        # 简单实现，可以使用更复杂的NLP模型
        text = text.strip()
        if text and not text[-1] in '。！？；':
            text += '。'
        return text
    
    def _convert_numbers(self, text: str) -> str:
        """数字转换"""
        # 简单的数字转换
        replacements = {
            "一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
            "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"
        }
        
        for chinese, arabic in replacements.items():
            text = text.replace(chinese, arabic)
        
        return text
    
    async def _update_recording_with_offline_results(
        self,
        recording_id: str,
        processed_segments: List[Dict[str, Any]],
        transcription_result: Dict[str, Any]
    ):
        """更新数据库中的离线处理结果"""
        try:
            # 保存新的段落（替换实时转写结果）
            db_manager.save_segments(recording_id, processed_segments)
            
            # 重新生成摘要（基于更准确的转写）
            full_text = " ".join([seg["content"] for seg in processed_segments])
            
            # 可以调用AI服务重新生成摘要
            from ai_service import ai_service
            summary_result = await ai_service.generate_summary(full_text, "meeting")
            if summary_result:
                db_manager.save_summary(recording_id, summary_result)
            
            # 重新提取关键词
            keywords_result = await ai_service.extract_keywords(full_text)
            if keywords_result:
                db_manager.save_keywords(recording_id, keywords_result)
            
            # 更新录音状态
            db_manager.update_recording_status(recording_id, "offline_completed")
            
            logger.info(f"录音 {recording_id} 离线处理结果已更新到数据库")
            
        except Exception as e:
            logger.error(f"更新离线处理结果失败: {e}")


# 全局离线处理器实例
offline_processor = OfflineAudioProcessor() 