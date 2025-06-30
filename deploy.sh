#!/bin/bash

echo "🚀 SenseVoice服务器部署脚本"
echo "================================"

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
    echo "❌ 请不要使用root用户运行此脚本"
    exit 1
fi

# 检查Python版本
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
if [[ $(echo "$python_version >= 3.8" | bc) -eq 0 ]]; then
    echo "❌ 需要Python 3.8或更高版本"
    exit 1
fi

echo "✅ Python版本: $python_version"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "📦 安装依赖包..."
pip install -r requirements.txt

# 检查SSL证书
if [ ! -f "cert.pem" ] || [ ! -f "key.pem" ]; then
    echo "⚠️  SSL证书文件不存在"
    echo "请确保以下文件存在："
    echo "  - cert.pem (SSL证书)"
    echo "  - key.pem (SSL私钥)"
    echo ""
    echo "生成自签名证书命令："
    echo "openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes"
    exit 1
fi

echo "✅ SSL证书文件检查通过"

# 检查端口
if netstat -tuln | grep -q ":8989 "; then
    echo "⚠️  端口8989已被占用"
    echo "请检查是否已有服务在运行"
fi

# 配置防火墙
echo "🔥 配置防火墙..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 8989/tcp
elif command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --permanent --add-port=8989/tcp
    sudo firewall-cmd --reload
fi

# 创建systemd服务
echo "⚙️  配置系统服务..."
current_dir=$(pwd)
current_user=$(whoami)

# 更新服务文件中的路径
sed -i "s|/home/ubuntu/api4sensevoice-main|$current_dir|g" sensevoice.service
sed -i "s|User=ubuntu|User=$current_user|g" sensevoice.service

# 安装服务
sudo cp sensevoice.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sensevoice

echo ""
echo "🎉 部署完成！"
echo "================================"
echo "启动服务: sudo systemctl start sensevoice"
echo "查看状态: sudo systemctl status sensevoice"
echo "查看日志: sudo journalctl -u sensevoice -f"
echo "访问地址: https://192.168.100.205:8989"
echo ""
echo "手动启动: ./start_server.sh"
echo "================================" 