#!/bin/bash

echo "🚀 山源听悟 - 服务器部署脚本"
echo "================================"
echo "目标服务器: 192.168.100.205"
echo "后端端口: 8989"
echo "前端端口: 5002"
echo "================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ 请不要使用root用户运行此脚本${NC}"
    exit 1
fi

# 检查系统依赖
echo -e "${BLUE}🔍 检查系统依赖...${NC}"

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3未安装${NC}"
    exit 1
fi

python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
if [[ $(echo "$python_version >= 3.8" | bc -l) -eq 0 ]]; then
    echo -e "${RED}❌ 需要Python 3.8或更高版本，当前版本: $python_version${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python版本: $python_version${NC}"

# 检查Node.js版本
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js未安装${NC}"
    exit 1
fi

node_version=$(node --version | grep -Po '(?<=v)\d+\.\d+')
if [[ $(echo "$node_version >= 16.0" | bc -l) -eq 0 ]]; then
    echo -e "${RED}❌ 需要Node.js 16.0或更高版本，当前版本: $node_version${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Node.js版本: $node_version${NC}"

# 检查pnpm
if ! command -v pnpm &> /dev/null; then
    echo -e "${YELLOW}⚠️  pnpm未安装，正在安装...${NC}"
    npm install -g pnpm
fi

# 检查Nginx
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}⚠️  Nginx未安装，请手动安装: sudo apt install nginx${NC}"
    read -p "是否继续部署（不使用Nginx）? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 第一步：部署后端
echo -e "${BLUE}📦 第一步：部署后端服务...${NC}"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}创建Python虚拟环境...${NC}"
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装Python依赖
echo -e "${YELLOW}安装Python依赖...${NC}"
pip install -r requirements.txt

# 检查SSL证书
echo -e "${BLUE}🔐 检查SSL证书...${NC}"
if [ ! -f "cert.pem" ] || [ ! -f "key.pem" ]; then
    echo -e "${YELLOW}⚠️  SSL证书文件不存在，正在生成自签名证书...${NC}"
    openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/C=CN/ST=State/L=City/O=Organization/OU=OrgUnit/CN=192.168.100.205"
    echo -e "${GREEN}✅ SSL证书生成完成${NC}"
fi

# 第二步：构建前端
echo -e "${BLUE}🎨 第二步：构建前端项目...${NC}"

cd voice-flow-meeting-vue

# 安装前端依赖
echo -e "${YELLOW}安装前端依赖...${NC}"
pnpm install

# 创建生产环境配置
echo -e "${YELLOW}创建生产环境配置...${NC}"
cat > .env.production << EOF
VITE_API_BASE_URL=https://192.168.100.205:8989
VITE_WS_URL=wss://192.168.100.205:8989
EOF

# 构建前端
echo -e "${YELLOW}构建前端项目...${NC}"
pnpm run build

# 创建前端部署目录
sudo mkdir -p /var/www/voice-flow-meeting
sudo cp -r dist/* /var/www/voice-flow-meeting/
sudo chown -R www-data:www-data /var/www/voice-flow-meeting

cd ..

# 第三步：配置系统服务
echo -e "${BLUE}⚙️  第三步：配置系统服务...${NC}"

current_dir=$(pwd)
current_user=$(whoami)

# 更新systemd服务文件
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

# 安装systemd服务
sudo cp sensevoice.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sensevoice

# 第四步：配置Nginx
echo -e "${BLUE}🌐 第四步：配置Nginx...${NC}"

if command -v nginx &> /dev/null; then
    # 创建Nginx配置
    cat > voice-flow-meeting.conf << EOF
# HTTP重定向到HTTPS
server {
    listen 5002 ssl http2;
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
        try_files $uri $uri/ /index.html;
        
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
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_connect_timeout 60;
        proxy_send_timeout 60;
    }

    # WebSocket代理
    location /ws/ {
        proxy_pass https://127.0.0.1:8989;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_connect_timeout 60;
        proxy_send_timeout 60;
    }
}
EOF

    # 安装Nginx配置
    sudo cp voice-flow-meeting.conf /etc/nginx/sites-available/
    sudo ln -sf /etc/nginx/sites-available/voice-flow-meeting.conf /etc/nginx/sites-enabled/
    
    # 测试Nginx配置
    if sudo nginx -t; then
        echo -e "${GREEN}✅ Nginx配置测试通过${NC}"
    else
        echo -e "${RED}❌ Nginx配置测试失败${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  跳过Nginx配置（未安装）${NC}"
fi

# 第五步：配置防火墙
echo -e "${BLUE}🔥 第五步：配置防火墙...${NC}"

if command -v ufw &> /dev/null; then
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw allow 8989/tcp
    echo -e "${GREEN}✅ UFW防火墙配置完成${NC}"
elif command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --permanent --add-port=80/tcp
    sudo firewall-cmd --permanent --add-port=443/tcp
    sudo firewall-cmd --permanent --add-port=8989/tcp
    sudo firewall-cmd --reload
    echo -e "${GREEN}✅ FirewallD防火墙配置完成${NC}"
fi

# 第六步：启动服务
echo -e "${BLUE}🚀 第六步：启动服务...${NC}"

# 启动后端服务
sudo systemctl start sensevoice
if sudo systemctl is-active --quiet sensevoice; then
    echo -e "${GREEN}✅ 后端服务启动成功${NC}"
else
    echo -e "${RED}❌ 后端服务启动失败${NC}"
    sudo systemctl status sensevoice
    exit 1
fi

# 启动Nginx
if command -v nginx &> /dev/null; then
    sudo systemctl enable nginx
    sudo systemctl restart nginx
    if sudo systemctl is-active --quiet nginx; then
        echo -e "${GREEN}✅ Nginx服务启动成功${NC}"
    else
        echo -e "${RED}❌ Nginx服务启动失败${NC}"
        sudo systemctl status nginx
        exit 1
    fi
fi

# 第七步：验证部署
echo -e "${BLUE}🔍 第七步：验证部署...${NC}"

sleep 3

# 检查后端API
if curl -k -s https://192.168.100.205:8989/api/health > /dev/null; then
    echo -e "${GREEN}✅ 后端API响应正常${NC}"
else
    echo -e "${YELLOW}⚠️  后端API响应异常，请检查日志${NC}"
fi

# 检查前端
if command -v nginx &> /dev/null; then
    if curl -k -s https://192.168.100.205:5002/ > /dev/null; then
        echo -e "${GREEN}✅ 前端页面响应正常${NC}"
    else
        echo -e "${YELLOW}⚠️  前端页面响应异常${NC}"
    fi
fi

echo ""
echo -e "${GREEN}🎉 部署完成！${NC}"
echo "================================"
echo -e "${BLUE}服务状态检查:${NC}"
echo "  后端服务: sudo systemctl status sensevoice"
echo "  前端服务: sudo systemctl status nginx"
echo ""
echo -e "${BLUE}日志查看:${NC}"
echo "  后端日志: sudo journalctl -u sensevoice -f"
echo "  Nginx日志: sudo tail -f /var/log/nginx/error.log"
echo ""
echo -e "${BLUE}访问地址:${NC}"
if command -v nginx &> /dev/null; then
    echo "  前端界面: https://192.168.100.205:5002"
    echo "  后端API: https://192.168.100.205:8989"
else
    echo "  直接访问: https://192.168.100.205:8989"
fi
echo ""
echo -e "${BLUE}管理命令:${NC}"
echo "  重启后端: sudo systemctl restart sensevoice"
echo "  重启前端: sudo systemctl restart nginx"
echo "  查看状态: sudo systemctl status sensevoice nginx"
echo "================================" 