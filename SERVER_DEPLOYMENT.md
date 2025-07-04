# 🚀 山源听悟 - 服务器部署指南

## 📋 部署概览

**目标服务器**: 192.168.100.205  
**架构**: 前后端分离部署  
**前端**: Vue3 + Vite + Nginx (端口 80/443)  
**后端**: FastAPI + Python (端口 8989)  

## 🛠️ 系统要求

### 基础环境
- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / 其他Linux发行版
- **Python**: 3.8+
- **Node.js**: 16.0+
- **内存**: 推荐 4GB+
- **存储**: 推荐 20GB+

### 依赖软件
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nodejs npm nginx openssl bc

# CentOS/RHEL
sudo yum install -y python3 python3-pip nodejs npm nginx openssl bc
```

## 🚀 一键部署

### 方法1: 使用自动部署脚本（推荐）

```bash
# 1. 进入项目目录
cd voice-flow-meeting

# 2. 给脚本添加执行权限
chmod +x deploy_to_server.sh

# 3. 运行部署脚本
./deploy_to_server.sh
```

### 方法2: 手动部署

#### 步骤1: 准备环境

```bash
# 检查Python版本
python3 --version  # 需要3.8+

# 检查Node.js版本
node --version     # 需要16.0+

# 安装pnpm
npm install -g pnpm
```

#### 步骤2: 部署后端

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 生成SSL证书（如果没有的话）
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
    -subj "/C=CN/ST=State/L=City/O=Organization/OU=OrgUnit/CN=192.168.100.205"
```

#### 步骤3: 构建前端

```bash
cd voice-flow-meeting-vue

# 安装依赖
pnpm install

# 创建生产环境配置
cat > .env.production << EOF
VITE_API_BASE_URL=https://192.168.100.205:8989
VITE_WS_URL=wss://192.168.100.205:8989
EOF

# 构建项目
pnpm run build

# 部署到Nginx目录
sudo mkdir -p /var/www/voice-flow-meeting
sudo cp -r dist/* /var/www/voice-flow-meeting/
sudo chown -R www-data:www-data /var/www/voice-flow-meeting

cd ..
```

#### 步骤4: 配置系统服务

```bash
# 创建systemd服务文件
current_dir=$(pwd)
current_user=$(whoami)

cat > sensevoice.service << EOF
[Unit]
Description=SenseVoice Real-time Speech Recognition Service
After=network.target

[Service]
Type=simple
User=$current_user
WorkingDirectory=$current_dir
Environment=PATH=$current_dir/venv/bin
ExecStart=$current_dir/venv/bin/python main.py --env server --port 8989 --host 0.0.0.0 --certfile cert.pem --keyfile key.pem
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 安装服务
sudo cp sensevoice.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sensevoice
```

#### 步骤5: 配置Nginx

```bash
# 创建Nginx站点配置
cat > voice-flow-meeting.conf << EOF
# HTTP重定向到HTTPS
server {
    listen 80;
    server_name 192.168.100.205;
    return 301 https://\$server_name\$request_uri;
}

# HTTPS前端服务
server {
    listen 443 ssl http2;
    server_name 192.168.100.205;

    ssl_certificate $current_dir/cert.pem;
    ssl_certificate_key $current_dir/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 前端静态文件
    location / {
        root /var/www/voice-flow-meeting;
        index index.html;
        try_files \$uri \$uri/ /index.html;
        
        # 设置缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API代理到后端
    location /api/ {
        proxy_pass https://127.0.0.1:8989;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
        proxy_connect_timeout 60;
        proxy_send_timeout 60;
    }

    # WebSocket代理
    location /ws/ {
        proxy_pass https://127.0.0.1:8989;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
        proxy_connect_timeout 60;
        proxy_send_timeout 60;
    }
}
EOF

# 安装配置
sudo cp voice-flow-meeting.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/voice-flow-meeting.conf /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t
```

#### 步骤6: 配置防火墙

```bash
# UFW (Ubuntu)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8989/tcp

# FirewallD (CentOS)
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=8989/tcp
sudo firewall-cmd --reload
```

#### 步骤7: 启动服务

```bash
# 启动后端服务
sudo systemctl start sensevoice
sudo systemctl status sensevoice

# 启动Nginx
sudo systemctl restart nginx
sudo systemctl status nginx
```

## 🔍 验证部署

### 检查服务状态
```bash
# 检查后端服务
sudo systemctl status sensevoice

# 检查Nginx服务
sudo systemctl status nginx

# 检查端口监听
sudo netstat -tlnp | grep -E ':(80|443|8989)'
```

### 测试访问
```bash
# 测试后端API
curl -k https://192.168.100.205:8989/api/health

# 测试前端页面
curl -k https://192.168.100.205/
```

### 浏览器访问
- **前端界面**: https://192.168.100.205
- **后端API**: https://192.168.100.205:8989

## 📊 服务管理

### 常用命令
```bash
# 重启服务
sudo systemctl restart sensevoice
sudo systemctl restart nginx

# 查看日志
sudo journalctl -u sensevoice -f
sudo tail -f /var/log/nginx/error.log

# 停止服务
sudo systemctl stop sensevoice
sudo systemctl stop nginx

# 查看服务状态
sudo systemctl status sensevoice nginx
```

### 更新部署
```bash
# 更新后端
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sensevoice

# 更新前端
cd voice-flow-meeting-vue
git pull
pnpm install
pnpm run build
sudo cp -r dist/* /var/www/voice-flow-meeting/
sudo systemctl restart nginx
```

## 🛠️ 故障排除

### 常见问题

#### 1. 后端服务启动失败
```bash
# 查看详细日志
sudo journalctl -u sensevoice -n 50

# 检查端口占用
sudo netstat -tlnp | grep 8989

# 检查SSL证书
ls -la cert.pem key.pem
```

#### 2. 前端页面无法访问
```bash
# 检查Nginx配置
sudo nginx -t

# 查看Nginx日志
sudo tail -f /var/log/nginx/error.log

# 检查文件权限
ls -la /var/www/voice-flow-meeting/
```

#### 3. API请求失败
```bash
# 检查防火墙
sudo ufw status
sudo firewall-cmd --list-all

# 检查后端服务
curl -k https://127.0.0.1:8989/api/health
```

#### 4. WebSocket连接失败
- 检查Nginx WebSocket代理配置
- 确认防火墙允许WebSocket连接
- 查看浏览器控制台错误信息

### 性能优化

#### 1. 系统资源监控
```bash
# 监控CPU和内存
htop
free -h

# 监控磁盘空间
df -h

# 监控网络连接
ss -tuln
```

#### 2. 服务优化
```bash
# 增加文件描述符限制
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf

# 优化Nginx配置
sudo nano /etc/nginx/nginx.conf
# 调整 worker_processes 和 worker_connections
```

## 📋 部署清单

### 部署前检查
- [ ] 服务器系统要求满足
- [ ] 网络连接正常
- [ ] 域名/IP地址配置正确
- [ ] 防火墙规则配置

### 部署过程检查
- [ ] Python环境配置完成
- [ ] Node.js环境配置完成
- [ ] 后端依赖安装成功
- [ ] 前端构建成功
- [ ] SSL证书生成/配置完成
- [ ] 系统服务配置完成
- [ ] Nginx配置完成

### 部署后验证
- [ ] 后端服务启动正常
- [ ] 前端服务启动正常
- [ ] API接口响应正常
- [ ] WebSocket连接正常
- [ ] 前端页面加载正常
- [ ] 文件上传功能正常
- [ ] 实时转写功能正常

## 🎯 生产环境建议

### 安全性
- 使用正式SSL证书（Let's Encrypt或商业证书）
- 配置防火墙规则
- 定期更新系统和依赖
- 配置访问日志和监控

### 可靠性
- 配置数据库备份
- 设置日志轮转
- 监控服务状态
- 配置自动重启机制

### 性能
- 使用CDN加速静态资源
- 配置Nginx缓存
- 优化数据库查询
- 监控系统资源使用

---

🎉 **部署完成后，您就可以通过 https://192.168.100.205 访问山源听悟系统了！** 