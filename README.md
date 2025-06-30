# SenseVoice实时语音识别服务

基于SenseVoice的实时语音识别和说话人验证服务，支持智能换行和聊天气泡界面。

## 功能特点

- 🎤 **实时语音识别**：基于SenseVoice模型的高精度中文语音识别
- 👥 **说话人识别**：基于CAM++模型的多说话人区分
- 💬 **聊天气泡界面**：类似通义听悟的现代化UI设计
- 🧠 **智能换行**：自动检测发言人变化和停顿，智能换行
- ⚡ **高性能**：异步处理，支持多并发连接
- 🔧 **易部署**：单文件启动，配置简单

## 项目结构

```
api4sensevoice-main/
├── main.py                    # 主服务器程序
├── index.html                 # 前端聊天界面
├── config.py                  # 配置文件
├── model_service.py           # AI模型服务
├── speaker_recognition.py     # 说话人识别算法
├── audio_buffer.py            # 音频缓冲区管理
├── text_processing.py         # 文本格式化处理
├── model.py                   # SenseVoice模型定义
├── requirements.txt           # Python依赖
├── speaker/                   # 测试音频样本
└── README.md                  # 说明文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python main.py --port 27000
```

### 3. 访问界面

打开浏览器访问：`http://localhost:27000`

或直接打开 `index.html` 文件

## 使用方法

1. **选择语言**：支持中文、英文、日语、韩语、粤语
2. **开启说话人识别**：勾选"区分发言人"选项
3. **智能换行**：默认开启，自动检测换行时机
4. **开始录音**：点击"开始录音"按钮
5. **查看结果**：实时显示识别结果，不同说话人用不同颜色区分

## API接口

### WebSocket接口

**连接地址**：`ws://localhost:27000/ws/transcribe`

**查询参数**：
- `sv`：是否启用说话人验证（true/false，默认false）
- `lang`：语言设置（zh/en/ja/ko/yue/auto，默认auto）

**示例**：`ws://localhost:27000/ws/transcribe?sv=true&lang=zh`

**响应格式**：
```json
{
  "code": 0,
  "msg": "{\"key\": \"...\", \"text\": \"...\"}",
  "data": "[发言人1]: 识别的文本内容",
  "speaker_id": "发言人1",
  "is_new_line": true,
  "segment_type": "new_speaker",
  "timestamp": 1640995200.0
}
```

## 配置说明

主要配置项在 `config.py` 中：

- `sv_thr`：说话人验证阈值（默认0.42）
- `chunk_size_ms`：音频块大小（默认300ms）
- `pause_threshold_ms`：停顿换行阈值（默认1500ms）
- `enable_smart_line_break`：是否启用智能换行（默认true）

## 性能特点

- **模型优化**：使用CAM++替代ERES2Net，参数量减少70%，性能提升23%
- **异步处理**：全异步架构，支持高并发
- **内存管理**：智能缓冲区管理，防止内存泄漏
- **实时性**：端到端延迟小于500ms

## 技术栈

- **语音识别**：SenseVoice (阿里达摩院)
- **说话人识别**：CAM++ (中科院自动化所)
- **后端框架**：FastAPI + WebSocket
- **前端技术**：原生JavaScript + CSS3
- **音频处理**：Web Audio API

## 许可证

MIT License
