# SenseVoice 实时语音识别服务 - 项目结构说明

## 项目概述

本项目是基于SenseVoice的实时语音识别服务，经过模块化重构，提高了代码的可维护性和可扩展性。

## 文件结构

### 核心模块文件

```
├── main.py                     # 主服务器文件 - 应用入口点
├── config.py                   # 配置模块 - 所有配置项和日志设置
├── model_service.py            # 模型服务模块 - AI模型管理和调用
├── audio_buffer.py             # 音频缓冲区模块 - 高效音频数据缓冲
├── speaker_recognition.py      # 说话人识别模块 - 说话人验证和识别
├── text_processing.py          # 文本处理模块 - 文本格式化功能
├── websocket_handler.py        # WebSocket处理模块 - 音频流处理
└── server_wss.py              # 原始单体文件 (已拆分, 保留备份)
```

### 其他文件

```
├── model.py                    # SenseVoice模型定义
├── requirements.txt            # Python依赖包
├── README.md                   # 项目说明文档
├── client_wss.html            # 客户端测试页面
├── nohup.out                  # 后台运行日志
└── speaker/                   # 说话人音频样本目录
    ├── speaker1_a_cn_16k.wav
    ├── speaker1_b_cn_16k.wav
    └── speaker2_a_cn_16k.wav
```

## 模块功能详解

### 1. main.py - 主服务器
- **功能**: FastAPI应用入口点，路由配置，全局异常处理
- **主要组件**:
  - FastAPI应用实例
  - CORS中间件配置
  - 全局异常处理器
  - 健康检查端点
  - WebSocket端点

### 2. config.py - 配置模块
- **功能**: 集中管理所有配置项和日志设置
- **主要配置**:
  - 音频参数 (采样率、块大小等)
  - 说话人识别参数 (阈值、音频长度限制等)
  - 线程池配置
  - 缓冲区配置
  - 日志配置函数

### 3. model_service.py - 模型服务
- **功能**: AI模型的加载、管理和异步调用
- **主要组件**:
  - 模型初始化函数
  - 线程池执行器
  - 异步模型推理包装函数
  - 应用生命周期管理

### 4. audio_buffer.py - 音频缓冲区
- **功能**: 高效的音频数据缓冲和管理
- **主要类**:
  - `AudioBuffer`: 基于deque的动态缓冲区
  - `CircularAudioBuffer`: 固定大小的循环缓冲区
- **优势**: 避免了np.append的O(n)性能问题

### 5. speaker_recognition.py - 说话人识别
- **功能**: 说话人验证和在线说话人日志分析
- **主要功能**:
  - 音频质量检查
  - 异步说话人验证
  - 动态阈值调整
  - 说话人连续性判断
  - 新说话人检测

### 6. text_processing.py - 文本处理
- **功能**: 语音识别结果的文本格式化
- **主要功能**:
  - 表情符号映射
  - 事件标签处理
  - 多语言标签处理
  - 文本内容验证

### 7. websocket_handler.py - WebSocket处理
- **功能**: WebSocket连接管理和音频流处理
- **主要功能**:
  - WebSocket连接处理
  - 音频流接收和缓冲
  - VAD检测和语音段提取
  - 异步音频处理管道
  - 响应数据格式化

## 性能优化亮点

### 1. 异步并发处理
- 使用线程池处理AI模型推理
- 并发执行说话人验证
- 非阻塞音频流处理

### 2. 高效音频缓冲
- 自定义音频缓冲区类
- O(1)时间复杂度的操作
- 固定内存占用的循环缓冲区

### 3. 智能说话人识别
- 动态阈值调整
- 音频质量检查
- 说话人连续性判断
- 历史记录维护

## 使用方式

### 启动服务
```bash
# 使用新的模块化版本
python main.py --port 27000

# 或者使用原始版本
python server_wss.py --port 27000
```

### 配置参数
在 `config.py` 中修改相关配置:
```python
class Config(BaseSettings):
    sv_thr: float = 0.42  # 说话人验证阈值
    chunk_size_ms: int = 300  # 音频块大小
    thread_pool_max_workers: int = 4  # 线程池大小
    # ... 其他配置
```

### WebSocket连接
```javascript
// 启用说话人验证
ws://localhost:27000/ws/transcribe?sv=true&lang=auto

// 仅语音识别
ws://localhost:27000/ws/transcribe?sv=false&lang=zh
```

## 迁移指南

### 从原版本迁移
1. 使用 `main.py` 替代 `server_wss.py` 启动服务
2. 配置项现在集中在 `config.py` 中
3. API接口和WebSocket协议保持不变
4. 客户端代码无需修改

### 扩展开发
1. 新增配置项: 在 `config.py` 中添加
2. 新增AI模型: 在 `model_service.py` 中扩展
3. 新增文本处理: 在 `text_processing.py` 中扩展
4. 新增WebSocket功能: 在 `websocket_handler.py` 中扩展

## 优势对比

| 特性 | 原版本 | 模块化版本 |
|------|--------|------------|
| 文件结构 | 单个854行文件 | 7个功能模块 |
| 可维护性 | 低 | 高 |
| 测试友好度 | 低 | 高 |
| 扩展性 | 差 | 好 |
| 性能 | 优化后 | 保持优化 |
| 配置管理 | 分散 | 集中化 |

## 注意事项

1. **向后兼容**: 新版本与原版本API完全兼容
2. **性能**: 保持了所有性能优化
3. **配置**: 配置项集中管理，更易维护
4. **测试**: 每个模块可独立测试
5. **部署**: 部署方式不变，仅需切换入口文件 