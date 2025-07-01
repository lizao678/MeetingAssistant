"""
AI服务模块 - 集成通义模型API
"""

import os
import re
import jieba
import jieba.posseg as pseg
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import dashscope
from dashscope import Generation
import asyncio
import httpx
from loguru import logger
import json


class AIService:
    """AI服务类，提供智能摘要、关键词提取等功能"""
    
    def __init__(self, api_key: str = None):
        """初始化AI服务
        
        Args:
            api_key: 通义模型API密钥
        """
        self.api_key = api_key or os.getenv('DASHSCOPE_API_KEY')
        if self.api_key:
            dashscope.api_key = self.api_key
        
        # 初始化jieba
        jieba.initialize()
        
        # 停用词集合
        self.stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '什么', '这个', '那个', '里', '这里', '那里', '现在', '时候', '可以', '还', '把', '他', '她', '它', '我们', '你们', '他们', '她们', '它们', '这些', '那些', '但是', '然后', '因为', '所以', '如果', '虽然', '只是', '应该', '可能', '已经', '还是', '或者', '而且', '但', '然', '因', '所', '如', '虽', '只', '应', '可', '已', '还', '或', '而'
        }
    
    async def generate_summary(self, text: str, summary_type: str = "meeting") -> Dict[str, Any]:
        """生成智能摘要
        
        Args:
            text: 原始文本
            summary_type: 摘要类型 (meeting, interview, lecture等)
            
        Returns:
            包含摘要内容和质量评分的字典
        """
        try:
            if not text or len(text.strip()) < 50:
                return {
                    "content": "抱歉，文本内容过短，无法生成有效摘要",
                    "quality": 1,
                    "word_count": 0,
                    "key_points": []
                }
            
            # 根据类型选择提示词
            prompts = {
                "meeting": """请为以下会议记录生成智能摘要。要求：
1. 总结主要议题和讨论要点
2. 提取关键决策和行动项
3. 突出重要信息和结论
4. 控制摘要长度在200字以内
5. 使用简洁清晰的语言

会议记录：
{text}

请以以下格式输出：
主要议题：[议题内容]
讨论要点：[要点1、要点2、要点3...]
关键决策：[决策内容]
行动项：[行动项内容]""",
                
                "interview": """请为以下访谈记录生成智能摘要。要求：
1. 总结访谈的主要内容和观点
2. 提取受访者的核心观点
3. 突出重要信息和见解
4. 控制摘要长度在200字以内

访谈记录：
{text}

请生成结构化摘要。""",
                
                "lecture": """请为以下讲座内容生成智能摘要。要求：
1. 总结讲座的主要内容
2. 提取核心知识点
3. 突出重要概念和结论
4. 控制摘要长度在200字以内

讲座内容：
{text}

请生成结构化摘要。"""
            }
            
            prompt = prompts.get(summary_type, prompts["meeting"]).format(text=text[:4000])  # 限制输入长度
            
            response = await asyncio.to_thread(
                Generation.call,
                model='qwen-turbo',
                prompt=prompt,
                max_tokens=500,
                temperature=0.3
            )
            
            if response.status_code == 200:
                summary_content = response.output.text.strip()
                
                # 评估摘要质量
                quality_score = self._evaluate_summary_quality(text, summary_content)
                
                # 提取关键点
                key_points = self._extract_key_points(summary_content)
                
                return {
                    "content": summary_content,
                    "quality": quality_score,
                    "word_count": len(summary_content),
                    "key_points": key_points,
                    "original_length": len(text),
                    "compression_ratio": round(len(summary_content) / len(text), 2)
                }
            else:
                logger.error(f"摘要生成失败: {response.message}")
                return self._fallback_summary(text)
                
        except Exception as e:
            logger.error(f"生成摘要时出错: {str(e)}")
            return self._fallback_summary(text)
    
    async def extract_keywords(self, text: str, max_keywords: int = 20) -> List[Dict[str, Any]]:
        """提取关键词
        
        Args:
            text: 原始文本
            max_keywords: 最大关键词数量
            
        Returns:
            关键词列表，包含词语、频次和重要性评分
        """
        try:
            if not text or len(text.strip()) < 20:
                return []
            
            # 使用jieba进行分词和词性标注
            words = pseg.cut(text)
            
            # 过滤有意义的词
            meaningful_words = []
            for word, flag in words:
                if (len(word) >= 2 and 
                    word not in self.stop_words and
                    flag in ['n', 'nr', 'ns', 'nt', 'nz', 'v', 'vn', 'a', 'ad', 'an']):  # 名词、动词、形容词
                    meaningful_words.append(word)
            
            # 统计词频
            word_freq = Counter(meaningful_words)
            
            # 使用AI模型提取更精准的关键词
            ai_keywords = await self._ai_extract_keywords(text)
            
            # 合并结果
            final_keywords = []
            processed_words = set()
            
            # 优先处理AI提取的关键词
            for ai_word in ai_keywords:
                if ai_word in word_freq and ai_word not in processed_words:
                    score = min(0.9, word_freq[ai_word] / len(meaningful_words) * 10)
                    final_keywords.append({
                        "word": ai_word,
                        "count": word_freq[ai_word],
                        "score": score,
                        "source": "ai"
                    })
                    processed_words.add(ai_word)
            
            # 添加高频词
            for word, count in word_freq.most_common(max_keywords * 2):
                if word not in processed_words:
                    score = min(0.8, count / len(meaningful_words) * 10)
                    final_keywords.append({
                        "word": word,
                        "count": count,
                        "score": score,
                        "source": "freq"
                    })
                    processed_words.add(word)
            
            # 按评分排序并限制数量
            final_keywords.sort(key=lambda x: x["score"], reverse=True)
            return final_keywords[:max_keywords]
            
        except Exception as e:
            logger.error(f"提取关键词时出错: {str(e)}")
            return self._fallback_keywords(text, max_keywords)
    
    async def _ai_extract_keywords(self, text: str) -> List[str]:
        """使用AI模型提取关键词"""
        try:
            prompt = f"""请从以下文本中提取最重要的关键词，要求：
1. 提取5-10个最核心的关键词
2. 关键词应该是名词、动词或重要概念
3. 避免通用词汇，关注专业术语和核心概念
4. 只返回关键词，用逗号分隔

文本：
{text[:2000]}

关键词："""

            response = await asyncio.to_thread(
                Generation.call,
                model='qwen-turbo',
                prompt=prompt,
                max_tokens=100,
                temperature=0.1
            )
            
            if response.status_code == 200:
                keywords_text = response.output.text.strip()
                keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
                return keywords[:10]
            else:
                return []
                
        except Exception as e:
            logger.error(f"AI关键词提取失败: {str(e)}")
            return []
    
    def _evaluate_summary_quality(self, original_text: str, summary: str) -> int:
        """评估摘要质量 (1-5分)"""
        try:
            # 基础评分标准
            score = 3
            
            # 长度合理性 (摘要应该是原文的10-30%)
            compression_ratio = len(summary) / len(original_text)
            if 0.1 <= compression_ratio <= 0.3:
                score += 1
            elif compression_ratio > 0.5:
                score -= 1
            
            # 内容完整性 (检查是否包含关键信息)
            if len(summary) > 50 and '：' in summary:
                score += 1
            
            # 结构清晰性
            if any(marker in summary for marker in ['主要', '重要', '关键', '总结', '议题', '要点']):
                score += 0.5
            
            # 语言流畅性 (简单检查)
            if not re.search(r'[。，、；：]{2,}', summary):  # 避免标点符号重复
                score += 0.5
            
            return max(1, min(5, int(score)))
            
        except Exception:
            return 3
    
    def _extract_key_points(self, summary: str) -> List[str]:
        """从摘要中提取关键要点"""
        try:
            key_points = []
            
            # 使用正则表达式提取结构化信息
            patterns = [
                r'主要议题[：:]\s*(.+?)(?=\n|讨论要点|关键决策|$)',
                r'讨论要点[：:]\s*(.+?)(?=\n|关键决策|行动项|$)',
                r'关键决策[：:]\s*(.+?)(?=\n|行动项|$)',
                r'行动项[：:]\s*(.+?)(?=\n|$)'
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, summary, re.MULTILINE | re.DOTALL)
                for match in matches:
                    content = match.group(1).strip()
                    if content and len(content) > 5:
                        # 分割多个要点
                        points = re.split(r'[、，,；;]', content)
                        for point in points:
                            point = point.strip()
                            if point and len(point) > 3:
                                key_points.append(point)
            
            return key_points[:5]  # 限制要点数量
            
        except Exception:
            return []
    
    def _fallback_summary(self, text: str) -> Dict[str, Any]:
        """降级摘要生成方案"""
        try:
            # 简单的摘要生成
            sentences = re.split(r'[。！？；]', text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
            
            if len(sentences) <= 3:
                summary = text[:200] + "..." if len(text) > 200 else text
            else:
                # 选择前几个句子作为摘要
                summary = "。".join(sentences[:3]) + "。"
            
            return {
                "content": summary,
                "quality": 2,
                "word_count": len(summary),
                "key_points": [],
                "fallback": True
            }
        except Exception:
            return {
                "content": "无法生成摘要",
                "quality": 1,
                "word_count": 0,
                "key_points": [],
                "fallback": True
            }
    
    def _fallback_keywords(self, text: str, max_keywords: int) -> List[Dict[str, Any]]:
        """降级关键词提取方案"""
        try:
            words = jieba.cut(text)
            meaningful_words = [w for w in words if len(w) >= 2 and w not in self.stop_words]
            word_freq = Counter(meaningful_words)
            
            keywords = []
            for word, count in word_freq.most_common(max_keywords):
                keywords.append({
                    "word": word,
                    "count": count,
                    "score": min(0.7, count / len(meaningful_words) * 10),
                    "source": "fallback"
                })
            
            return keywords
        except Exception:
            return []
    
    async def analyze_speaker_activity(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析说话人活跃度"""
        try:
            speaker_stats = {}
            total_duration = 0
            
            for segment in segments:
                speaker_id = segment.get('speaker_id', 'Unknown')
                duration = segment.get('end_time', 0) - segment.get('start_time', 0)
                word_count = len(segment.get('text', '').split())
                
                if speaker_id not in speaker_stats:
                    speaker_stats[speaker_id] = {
                        'total_time': 0,
                        'segment_count': 0,
                        'word_count': 0,
                        'avg_segment_length': 0
                    }
                
                speaker_stats[speaker_id]['total_time'] += duration
                speaker_stats[speaker_id]['segment_count'] += 1
                speaker_stats[speaker_id]['word_count'] += word_count
                total_duration += duration
            
            # 计算统计数据
            for speaker_id in speaker_stats:
                stats = speaker_stats[speaker_id]
                stats['avg_segment_length'] = stats['total_time'] / stats['segment_count'] if stats['segment_count'] > 0 else 0
                stats['time_percentage'] = (stats['total_time'] / total_duration * 100) if total_duration > 0 else 0
                stats['words_per_minute'] = (stats['word_count'] / (stats['total_time'] / 60)) if stats['total_time'] > 0 else 0
            
            return {
                'speaker_stats': speaker_stats,
                'total_speakers': len(speaker_stats),
                'total_duration': total_duration,
                'most_active_speaker': max(speaker_stats.keys(), key=lambda x: speaker_stats[x]['total_time']) if speaker_stats else None
            }
            
        except Exception as e:
            logger.error(f"分析说话人活跃度时出错: {str(e)}")
            return {}


# 全局AI服务实例
ai_service = AIService() 