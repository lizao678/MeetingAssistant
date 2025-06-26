"""
音频缓冲区模块 - 高效的音频数据缓冲区实现
"""

import numpy as np
from collections import deque
from typing import Optional


class AudioBuffer:
    """
    高效的音频缓冲区实现，使用deque避免np.append的性能问题
    """
    def __init__(self, max_size: Optional[int] = None, dtype=np.float32):
        self.chunks = deque(maxlen=max_size)
        self.dtype = dtype
        self._total_length = 0
        
    def append(self, data: np.ndarray):
        """添加新的音频数据"""
        if len(data) > 0:
            self.chunks.append(data.astype(self.dtype))
            self._total_length += len(data)
    
    def get_data(self, start_idx: int = 0, length: Optional[int] = None) -> np.ndarray:
        """获取指定范围的音频数据"""
        if not self.chunks:
            return np.array([], dtype=self.dtype)
        
        # 合并所有chunks
        combined = np.concatenate(list(self.chunks))
        
        if length is None:
            return combined[start_idx:]
        else:
            end_idx = start_idx + length
            return combined[start_idx:min(end_idx, len(combined))]
    
    def pop_front(self, length: int) -> np.ndarray:
        """从前面弹出指定长度的数据"""
        if not self.chunks:
            return np.array([], dtype=self.dtype)
        
        result_data = []
        remaining_length = length
        
        while remaining_length > 0 and self.chunks:
            chunk = self.chunks[0]
            
            if len(chunk) <= remaining_length:
                # 整个chunk都要被弹出
                result_data.append(self.chunks.popleft())
                remaining_length -= len(chunk)
                self._total_length -= len(chunk)
            else:
                # 只弹出chunk的一部分
                result_data.append(chunk[:remaining_length])
                # 更新第一个chunk
                self.chunks[0] = chunk[remaining_length:]
                self._total_length -= remaining_length
                remaining_length = 0
        
        return np.concatenate(result_data) if result_data else np.array([], dtype=self.dtype)
    
    def __len__(self) -> int:
        """返回缓冲区中的总样本数"""
        return self._total_length
    
    def clear(self):
        """清空缓冲区"""
        self.chunks.clear()
        self._total_length = 0
    
    def slice_and_keep_rest(self, start_idx: int, end_idx: int) -> np.ndarray:
        """切片数据并保留剩余部分"""
        if not self.chunks:
            return np.array([], dtype=self.dtype)
        
        # 获取所有数据
        all_data = np.concatenate(list(self.chunks))
        
        # 提取指定范围的数据
        sliced_data = all_data[start_idx:end_idx]
        
        # 保留剩余数据
        remaining_data = all_data[end_idx:]
        
        # 重新设置缓冲区
        self.clear()
        if len(remaining_data) > 0:
            self.append(remaining_data)
        
        return sliced_data


class CircularAudioBuffer:
    """
    循环音频缓冲区，用于VAD处理，避免频繁的内存分配
    """
    def __init__(self, max_samples: int, dtype=np.float32):
        self.buffer = np.zeros(max_samples, dtype=dtype)
        self.max_samples = max_samples
        self.write_pos = 0
        self.read_pos = 0
        self.size = 0
        self.dtype = dtype
    
    def append(self, data: np.ndarray):
        """添加数据到循环缓冲区"""
        data = data.astype(self.dtype)
        data_len = len(data)
        
        # 如果数据太大，只保留最后的部分
        if data_len >= self.max_samples:
            self.buffer[:] = data[-self.max_samples:]
            self.write_pos = 0
            self.read_pos = 0
            self.size = self.max_samples
            return
        
        # 计算可用空间
        available_space = self.max_samples - self.size
        
        if data_len <= available_space:
            # 有足够空间，直接添加
            end_pos = self.write_pos + data_len
            if end_pos <= self.max_samples:
                self.buffer[self.write_pos:end_pos] = data
            else:
                # 需要环绕
                split_point = self.max_samples - self.write_pos
                self.buffer[self.write_pos:] = data[:split_point]
                self.buffer[:end_pos - self.max_samples] = data[split_point:]
            
            self.write_pos = end_pos % self.max_samples
            self.size += data_len
        else:
            # 空间不足，覆盖旧数据
            overwrite_count = data_len - available_space
            
            # 先添加到可用空间
            if available_space > 0:
                self.append(data[:available_space])
            
            # 然后覆盖旧数据
            self.read_pos = (self.read_pos + overwrite_count) % self.max_samples
            self.size -= overwrite_count
            
            # 添加剩余数据
            self.append(data[available_space:])
    
    def get_range(self, start_offset: int, length: int) -> np.ndarray:
        """获取指定范围的数据"""
        if length <= 0 or start_offset >= self.size:
            return np.array([], dtype=self.dtype)
        
        # 调整长度以不超过可用数据
        actual_length = min(length, self.size - start_offset)
        result = np.zeros(actual_length, dtype=self.dtype)
        
        start_pos = (self.read_pos + start_offset) % self.max_samples
        end_pos = start_pos + actual_length
        
        if end_pos <= self.max_samples:
            result[:] = self.buffer[start_pos:end_pos]
        else:
            # 需要环绕读取
            first_part_len = self.max_samples - start_pos
            result[:first_part_len] = self.buffer[start_pos:]
            result[first_part_len:] = self.buffer[:actual_length - first_part_len]
        
        return result
    
    def pop_front(self, length: int) -> np.ndarray:
        """从前面弹出数据"""
        if length <= 0 or self.size == 0:
            return np.array([], dtype=self.dtype)
        
        actual_length = min(length, self.size)
        result = self.get_range(0, actual_length)
        
        # 更新读取位置和大小
        self.read_pos = (self.read_pos + actual_length) % self.max_samples
        self.size -= actual_length
        
        return result
    
    def __len__(self) -> int:
        return self.size
    
    def clear(self):
        """清空缓冲区"""
        self.write_pos = 0
        self.read_pos = 0
        self.size = 0 