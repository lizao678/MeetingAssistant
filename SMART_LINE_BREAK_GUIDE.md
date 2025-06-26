# SenseVoice 智能换行功能说明

## 功能概述

智能换行功能解决了您提出的"一段时间不说话就识别不了了"的问题，并增强了前端显示效果。

## 主要改进

### 1. 问题解决
- **VAD缓冲区溢出修复**: 增加了智能缓冲区管理，防止长时间静音导致的识别失败
- **偏移量累积错误修复**: 添加了定期重置机制，避免时间戳计算错误
- **停顿检测优化**: 30秒无语音活动后自动重置缓冲区状态

### 2. 智能换行逻辑
根据以下情况决定是否换行：

#### 换行触发条件
1. **发言人变化**: 当检测到不同的说话人时自动换行
2. **长停顿**: 当同一发言人停顿超过阈值时间（默认1.5秒）时换行
3. **首次识别**: 会话开始时的第一次识别结果

#### 连续显示条件
- 同一发言人连续说话（停顿少于阈值）
- 前端将新识别的文本接在当前行后面

## 配置参数

### VAD缓冲区管理
```python
vad_buffer_seconds: int = 15  # VAD缓冲区大小（秒）
vad_buffer_cleanup_threshold: float = 0.8  # 清理阈值（80%容量时开始清理）
vad_buffer_cleanup_ratio: float = 0.3  # 清理比例（清理30%的旧数据）
silence_reset_seconds: int = 30  # 静音重置时间（秒）
keep_audio_seconds: int = 5  # 重置后保留的音频时长（秒）
```

### 智能换行控制
```python
pause_threshold_ms: int = 1500  # 停顿阈值（毫秒）
enable_smart_line_break: bool = True  # 启用智能换行
```

## 响应格式

### 新的响应字段
```json
{
    "code": 0,
    "msg": "识别详情JSON",
    "data": "识别文本或[发言人]: 识别文本",
    "speaker_id": "发言人1",
    "is_new_line": true,
    "segment_type": "new_speaker",
    "timestamp": 1703123456.789
}
```

### segment_type 类型
- `"new_speaker"`: 发言人变化
- `"pause"`: 长停顿
- `"continue"`: 连续说话
- `"traditional"`: 传统模式（每次都换行）

## 前端使用

### HTML客户端更新
1. 添加了"智能换行"复选框控制
2. 根据 `is_new_line` 字段决定显示方式：
   - `true`: 换行显示（包含说话人标识）
   - `false`: 接在当前行后面（纯文本）

### 示例代码
```javascript
if (smartLineBreakEnabled && resJson.is_new_line !== undefined) {
    // 智能换行模式
    if (resJson.is_new_line) {
        transcriptionResult.textContent += "\n" + text;  // 换行
    } else {
        transcriptionResult.textContent += text;  // 继续
    }
} else {
    // 传统模式
    transcriptionResult.textContent += "\n" + text;  // 每次都换行
}
```

## 使用效果

### 智能换行模式效果
```
[发言人1]: 大家好，我是张三
今天我们来讨论一下项目进度的问题
这个月我们完成了很多重要的功能

[发言人2]: 是的，我觉得进展不错
但是还有一些地方需要改进
特别是性能优化方面

[发言人1]: 你说得对
我们下周专门安排时间来处理这个问题
```

### 传统模式效果
```
[发言人1]: 大家好，我是张三
[发言人1]: 今天我们来讨论一下项目进度的问题
[发言人1]: 这个月我们完成了很多重要的功能
[发言人2]: 是的，我觉得进展不错
[发言人2]: 但是还有一些地方需要改进
[发言人2]: 特别是性能优化方面
```

## 测试方法

### 1. 启动服务
```bash
python main.py --port 27000
```

### 2. 使用测试脚本
```bash
python test_smart_line_break.py
```

### 3. 使用Web客户端
打开 `client_wss.html`，勾选"智能换行"选项进行测试

## 调优建议

### 调整停顿阈值
根据使用场景调整 `pause_threshold_ms`：
- 快节奏对话: 800-1200ms
- 正常对话: 1200-1800ms  
- 慢节奏演讲: 1800-3000ms

### 禁用智能换行
如果希望保持传统的每次换行行为，设置：
```python
enable_smart_line_break: bool = False
```

## 兼容性

- 新版本完全向后兼容
- 旧的客户端会自动采用传统换行模式
- 新客户端可以选择启用或禁用智能换行

## 性能影响

- 智能换行逻辑开销极小（毫秒级）
- VAD缓冲区优化实际上提升了整体性能
- 内存使用更加稳定和可预测 