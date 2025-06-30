# 部署指南

本应用支持自动环境检测，可以在本地开发和服务器生产环境之间无缝切换。

## 🏠 本地开发环境

### 快速启动
```bash
# Windows
start_local.bat

# Linux/Mac
./start_local.sh

# 或者直接使用Python命令
python main.py --env local --port 26000
```

### 本地环境配置
- **协议**: HTTP (ws://)
- **地址**: 127.0.0.1:26000
- **SSL**: 禁用
- **前端自动检测**: 当通过 localhost 或 127.0.0.1 访问时自动使用本地配置

## 🌐 服务器生产环境

### 前提条件
需要准备SSL证书文件：
- `cert.pem` - SSL证书文件
- `key.pem` - SSL私钥文件

### 快速启动
```bash
# Windows
start_server.bat

# Linux/Mac
./start_server.sh

# 或者直接使用Python命令
python main.py --env server --port 8989 --certfile cert.pem --keyfile key.pem
```

### 服务器环境配置
- **协议**: HTTPS (wss://)
- **地址**: 192.168.100.205:8989
- **SSL**: 启用
- **前端自动检测**: 当通过服务器IP访问时自动使用服务器配置

## 🔧 环境自动检测机制

### 后端检测
- 如果提供了 `--certfile` 和 `--keyfile` 参数，自动启用SSL
- 可以手动指定 `--env` 参数强制使用特定环境

### 前端检测
前端JavaScript会根据访问地址自动选择配置：

```javascript
function detectEnvironment() {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    
    // 通过服务器IP访问 → 使用服务器配置
    if (hostname === '192.168.100.205' || hostname.includes('192.168.')) {
        return 'server';
    }
    // HTTPS访问 → 可能是服务器环境
    else if (protocol === 'https:') {
        return 'server';
    }
    // 其他情况 → 使用本地配置
    else {
        return 'local';
    }
}
```

## 📋 使用场景

### 场景1: 本地开发
1. 双击 `start_local.bat` (Windows) 或运行 `./start_local.sh` (Linux/Mac)
2. 浏览器访问: `http://127.0.0.1:26000`
3. 前端自动连接到: `ws://127.0.0.1:26000/ws/transcribe`

### 场景2: 服务器部署
1. 准备SSL证书文件 `cert.pem` 和 `key.pem`
2. 双击 `start_server.bat` (Windows) 或运行 `./start_server.sh` (Linux/Mac)
3. 浏览器访问: `https://192.168.100.205:8989`
4. 前端自动连接到: `wss://192.168.100.205:8989/ws/transcribe`

### 场景3: 手动控制
```bash
# 强制本地模式（即使提供了SSL证书）
python main.py --env local --port 26000

# 强制服务器模式（需要SSL证书）
python main.py --env server --port 8989 --certfile cert.pem --keyfile key.pem

# 自动检测模式（默认）
python main.py --env auto --port 26000
```

## 🔍 故障排除

### 问题1: 前端无法连接
**检查项**：
1. 确认后端服务已启动
2. 检查端口是否被占用
3. 查看浏览器控制台的WebSocket连接日志

### 问题2: SSL证书错误
**解决方案**：
1. 确认证书文件路径正确
2. 检查证书文件权限
3. 验证证书是否匹配服务器域名/IP

### 问题3: 环境检测错误
**调试方法**：
1. 打开浏览器开发者工具
2. 查看控制台输出的环境检测信息：
   ```
   当前访问: http://127.0.0.1:26000
   检测到环境: local
   使用配置: {host: "127.0.0.1", port: 26000, protocol: "ws", ssl: false}
   连接到: ws://127.0.0.1:26000/ws/transcribe
   ```

## 📝 配置文件

### env_config.json
```json
{
  "local": {
    "host": "127.0.0.1",
    "port": 26000,
    "protocol": "ws",
    "ssl": false
  },
  "server": {
    "host": "192.168.100.205",
    "port": 8989,
    "protocol": "wss",
    "ssl": true
  }
}
```

如需修改配置，同时更新：
1. `env_config.json` 文件
2. `index.html` 中的 `ENV_CONFIG` 对象
3. 启动脚本中的端口参数

## 🚀 快速测试

### 测试本地环境
```bash
python main.py --env local --port 26000
# 浏览器访问: http://127.0.0.1:26000
```

### 测试服务器环境（需要SSL证书）
```bash
python main.py --env server --port 8989 --certfile cert.pem --keyfile key.pem
# 浏览器访问: https://192.168.100.205:8989
```

现在您可以：
- 在本地开发时使用本地配置
- 部署到服务器时使用服务器配置
- 前端会自动检测环境并连接到正确的后端地址 