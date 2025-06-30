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

### 💻 本地开发环境

#### 1. 安装依赖

**使用国内镜像源（推荐）**：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

**或使用默认源**：
```bash
pip install -r requirements.txt
```

#### 2. 启动本地服务

**方式一：使用启动脚本（推荐）**

Windows:
```bash
start_local.bat
```

Linux/Mac:
```bash
chmod +x start_local.sh
./start_local.sh
```

**方式二：直接命令**
```bash
python main.py --env local --port 26000 --host 127.0.0.1
```

#### 3. 访问界面

打开浏览器访问：`http://127.0.0.1:26000`

### 🌐 服务器部署

#### 1. 准备SSL证书

确保SSL证书文件存在：
```bash
ls -la /path/to/ssl/cert.pem
ls -la /path/to/ssl/key.pem
```

#### 2. 启动服务器

**方式一：使用启动脚本**
```bash
# 需要先修改start_server.sh中的SSL证书路径
chmod +x start_server.sh
nohup ./start_server.sh &
```

**方式二：直接命令**
```bash
nohup python main.py --env server --port 8989 --host 0.0.0.0 --certfile /path/to/cert.pem --keyfile /path/to/key.pem &
```

#### 3. 查看日志和状态

```bash
# 查看启动日志
tail -f nohup.out

# 检查服务状态
ps aux | grep "main.py"

# 检查端口监听
netstat -tulpn | grep 8989

# 健康检查
curl -k https://localhost:8989/health
```

#### 4. 访问界面

浏览器访问：`https://您的服务器IP:8989`

### 🛠 管理命令

**停止服务**：
```bash
# 本地服务
pkill -f "main.py.*local"

# 服务器服务
pkill -f "main.py.*server"
```

**重启服务**：
```bash
# 停止 + 重新启动
pkill -f "main.py"
nohup python main.py --env server --port 8989 --host 0.0.0.0 --certfile /path/to/cert.pem --keyfile /path/to/key.pem &
```

## 使用方法

1. **选择语言**：支持中文、英文、日语、韩语、粤语
2. **开启说话人识别**：勾选"区分发言人"选项
3. **智能换行**：默认开启，自动检测换行时机
4. **开始录音**：点击"开始录音"按钮
5. **查看结果**：实时显示识别结果，不同说话人用不同颜色区分

## API接口

### WebSocket接口

**本地开发环境**：
- 连接地址：`ws://127.0.0.1:26000/ws/transcribe`
- 示例：`ws://127.0.0.1:26000/ws/transcribe?sv=true&lang=zh`

**服务器生产环境**：
- 连接地址：`wss://您的服务器IP:8989/ws/transcribe`
- 示例：`wss://192.168.100.205:8989/ws/transcribe?sv=true&lang=zh`

**查询参数**：
- `sv`：是否启用说话人验证（true/false，默认false）
- `lang`：语言设置（zh/en/ja/ko/yue/auto，默认auto）

### REST API

**健康检查**：
- 本地：`http://127.0.0.1:26000/health`
- 服务器：`https://您的服务器IP:8989/health`

**API信息**：
- 本地：`http://127.0.0.1:26000/api`
- 服务器：`https://您的服务器IP:8989/api`

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

## 常见问题

### Q: 依赖安装太慢怎么办？
A: 使用国内镜像源：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### Q: 端口被占用怎么办？
A: 检查端口占用并选择其他端口：
```bash
# 检查端口占用
netstat -tulpn | grep 26000

# 使用其他端口启动
python main.py --env local --port 26001 --host 127.0.0.1
```

### Q: 如何检查服务是否启动成功？
A: 使用以下命令检查：
```bash
# 检查进程
ps aux | grep "main.py"

# 检查端口监听
netstat -tulpn | grep 26000

# 健康检查
curl http://127.0.0.1:26000/health
```

### Q: 浏览器无法访问HTTPS服务？
A: 可能是SSL证书问题，在浏览器中：
1. 点击"高级"
2. 选择"继续访问（不安全）"
3. 或在本地添加证书信任

### Q: WebSocket连接失败？
A: 检查以下项目：
1. 后端服务是否正常启动
2. 端口是否正确
3. 防火墙是否开放相应端口
4. 浏览器是否支持WebSocket

### Q: 模型加载失败？
A: 确保：
1. 网络连接正常（首次运行需要下载模型）
2. 硬盘空间充足
3. 内存大小足够（建议8GB以上）

## 许可证

MIT License
