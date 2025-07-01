# 🎤 山源听悟 - SenseVoice AI语音识别平台

基于阿里巴巴SenseVoice的现代化语音识别解决方案，集成通义千问AI模型，提供高精度实时转写、智能总结、关键词提取和说话人识别功能。

## ✨ 功能特点

### 🎯 核心功能
- 🎤 **实时语音识别**：基于SenseVoice模型的高精度中文语音识别
- 👥 **说话人识别**：基于CAM++模型的多说话人区分，支持1-10人自动识别
- 🤖 **智能摘要**：集成通义千问，自动生成会议摘要、访谈总结
- 🏷️ **关键词提取**：AI驱动的关键词提取和重要性评分
- 📊 **数据分析**：说话人活跃度统计、发言时长分析

### 🎨 用户体验
- 💬 **现代化界面**：参考通义听悟的聊天气泡界面设计
- ⚡ **实时转写**：边说边转，延迟小于500ms
- 🧠 **智能换行**：自动检测发言人变化和停顿
- 🎵 **音频回放**：支持倍速播放、波形可视化、文本同步
- 📱 **响应式设计**：支持桌面和移动端

### 🔧 技术特色
- 🚀 **高性能**：异步处理，支持多并发连接
- 🛡️ **数据安全**：本地部署，数据不外传
- 📦 **易部署**：一键启动，配置简单
- 🔄 **完整流程**：录音→转写→AI分析→详情查看

## 🏗️ 项目架构

```
voice-flow-meeting/
├── 🐍 后端服务
│   ├── main.py                    # FastAPI主服务器
│   ├── ai_service.py              # AI服务(通义千问集成)
│   ├── recording_service.py       # 录音处理服务
│   ├── database.py                # 数据库模型
│   ├── model_service.py           # SenseVoice模型服务
│   ├── speaker_recognition.py     # 说话人识别
│   └── config.py                  # 配置管理
├── 🎨 前端应用 (Vue 3)
│   └── voice-flow-meeting-vue/
│       ├── src/components/        # 组件库
│       ├── src/views/             # 页面视图
│       ├── src/services/          # API服务
│       └── src/stores/            # 状态管理
└── 📄 配置文件
    ├── env_template.txt           # 环境配置模板
    ├── start_with_ai.py          # AI功能启动脚本
    └── requirements.txt           # Python依赖
```

## 🚀 快速开始

### 📋 环境要求

- Python 3.8+
- Node.js 16+ (前端开发)
- 通义千问API密钥 (AI功能)

### ⚡ 一键启动

#### 1. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 安装前端依赖 (如需前端开发)
cd voice-flow-meeting-vue
npm install
```

#### 2. 配置API密钥

```bash
# 复制配置模板
cp env_template.txt .env

# 编辑配置文件，填入您的通义千问API密钥
nano .env
```

在`.env`文件中设置：
```bash
DASHSCOPE_API_KEY=your_dashscope_api_key_here
```

#### 3. 启动服务

**使用AI启动脚本（推荐）**：
```bash
python start_with_ai.py
```

**或传统方式启动**：
```bash
python main.py --port 26000 --host 0.0.0.0
```

#### 4. 访问服务

- 🌐 **Web界面**: http://localhost:26000
- 📡 **WebSocket**: ws://localhost:26000/ws/transcribe
- 📊 **API文档**: http://localhost:26000/docs

## 📖 使用指南

### 🎙️ 实时转写

1. 打开Web界面
2. 选择语言和发言人数量
3. 点击"开始录音"
4. 实时查看转写结果

### 📋 录音分析流程

1. **录音结束** → 选择发言人数量
2. **AI处理** → 自动转写+说话人识别
3. **智能分析** → 生成摘要和关键词
4. **详情查看** → 完整的分析报告

### 🎵 音频回放功能

- ⏯️ 播放/暂停控制
- ⏩ 倍速播放 (0.5x - 2x)
- 📍 点击文本跳转到对应时间点
- 📊 波形可视化显示

## 🔌 API接口文档

### 📡 WebSocket接口

**实时转写连接**：
```
ws://localhost:26000/ws/transcribe?sv=true&lang=zh
```

**参数说明**：
- `sv`: 是否启用说话人验证 (true/false)
- `lang`: 语言设置 (zh/en/ja/ko/yue/auto)

### 🌐 REST API

#### 录音处理

**提交录音处理**：
```http
POST /api/recordings/process
Content-Type: multipart/form-data

audio_file: [音频文件]
speaker_count: 2
language: zh
smart_punctuation: true
generate_summary: true
summary_type: meeting
```

**获取处理状态**：
```http
GET /api/recordings/{recording_id}/status
```

**获取录音详情**：
```http
GET /api/recordings/{recording_id}/detail
```

#### 数据管理

**获取录音列表**：
```http
GET /api/recordings?page=1&page_size=20
```

**重新生成摘要**：
```http
POST /api/recordings/{recording_id}/regenerate-summary
Content-Type: application/json

{
  "summary_type": "meeting"
}
```

**下载录音文件**：
```http
GET /api/recordings/{recording_id}/download
```

#### 响应格式

```json
{
  "success": true,
  "data": {
    "recording": {
      "id": "uuid",
      "title": "录音标题",
      "duration": 120.5,
      "status": "completed"
    },
    "segments": [
      {
        "speaker_name": "发言人A",
        "content": "转写内容",
        "start_time": 0.0,
        "end_time": 5.2
      }
    ],
    "summary": {
      "content": "智能摘要内容",
      "quality": 4,
      "key_points": ["要点1", "要点2"]
    },
    "keywords": [
      {
        "word": "关键词",
        "count": 5,
        "score": 0.8
      }
    ]
  }
}
```

## 🤖 AI功能配置

### 🔑 获取通义千问API密钥

1. 访问 [阿里云DashScope控制台](https://dashscope.console.aliyun.com/)
2. 开通DashScope服务
3. 创建API密钥
4. 将密钥配置到`.env`文件

### ⚙️ AI服务配置

```bash
# .env 文件配置
DASHSCOPE_API_KEY=your_api_key_here
DEFAULT_SUMMARY_TYPE=meeting
MAX_KEYWORDS=20
```

**摘要类型**：
- `meeting`: 会议记录
- `interview`: 访谈记录  
- `lecture`: 讲座内容

## 🛠️ 开发指南

### 前端开发

```bash
cd voice-flow-meeting-vue

# 开发模式
npm run dev

# 构建生产版本
npm run build
```

### 后端开发

```bash
# 开发模式启动
python main.py --log-level debug

# 查看API文档
# 访问 http://localhost:26000/docs
```

### 数据库管理

项目使用SQLite数据库，文件位置：`recordings.db`

**查看数据**：
```bash
sqlite3 recordings.db
.tables
.schema recordings
```

## 📊 性能指标

### 🎯 识别精度
- 中文识别准确率：95%+
- 说话人识别准确率：90%+
- 端到端延迟：<500ms

### ⚡ 性能优化
- 模型参数量减少70%（CAM++ vs ERES2Net）
- 识别性能提升23%
- 支持10+并发连接
- 内存占用<2GB

## 🔧 配置参考

### config.py 主要配置

```python
# 音频处理
sample_rate = 16000
chunk_size_ms = 300

# 说话人识别
sv_thr = 0.42
pause_threshold_ms = 1500

# 智能换行
enable_smart_line_break = True

# 性能设置
thread_pool_max_workers = 4
audio_buffer_max_size = 32000
```

### 环境变量配置

```bash
# 服务配置
PORT=26000
HOST=0.0.0.0
LOG_LEVEL=info

# AI服务
DASHSCOPE_API_KEY=your_key
DEFAULT_SUMMARY_TYPE=meeting
MAX_KEYWORDS=20

# 数据库
DATABASE_URL=sqlite:///recordings.db

# 文件上传
UPLOAD_DIR=uploads
MAX_FILE_SIZE=100MB
```

## 🐛 故障排除

### 常见问题

**Q: AI功能不工作？**
A: 检查API密钥配置，确保网络连接正常

**Q: 录音文件上传失败？**
A: 检查文件大小限制和格式支持

**Q: 说话人识别不准确？**
A: 调整`sv_thr`阈值，确保音频质量

**Q: 前端无法连接后端？**
A: 检查端口配置和防火墙设置

### 日志查看

```bash
# 实时查看日志
tail -f logs/app.log

# 查看错误日志
grep "ERROR" logs/app.log
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork项目
2. 创建功能分支
3. 提交代码
4. 发起Pull Request

## 📄 许可证

本项目采用 MIT 许可证。

## 🙏 致谢

- [阿里达摩院SenseVoice](https://github.com/FunAudioLLM/SenseVoice)
- [通义千问](https://dashscope.aliyun.com/)
- [中科院自动化所CAM++](https://github.com/modelscope/3D-Speaker)

---

**🌟 如果这个项目对您有帮助，请给个Star支持一下！**
