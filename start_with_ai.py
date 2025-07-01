#!/usr/bin/env python3
"""
山源听悟 - AI功能启动脚本
自动设置环境变量并启动服务器
"""

import os
import sys
from pathlib import Path

def setup_environment():
    """设置环境变量"""
    print("🔧 正在设置环境变量...")
    
    # 检查是否有 .env 文件
    env_file = Path(".env")
    if env_file.exists():
        print("✅ 发现 .env 文件，正在加载配置...")
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            print("✅ 环境变量加载完成")
        except Exception as e:
            print(f"❌ 加载 .env 文件失败: {e}")
    else:
        print("⚠️  未找到 .env 文件")
        print("💡 请参考 env_template.txt 创建 .env 文件并配置您的API密钥")
        
        # 提示用户输入API密钥
        dashscope_key = input("请输入您的 DashScope API 密钥 (或按回车跳过): ").strip()
        if dashscope_key:
            os.environ['DASHSCOPE_API_KEY'] = dashscope_key
            print("✅ API密钥已设置")
        else:
            print("⚠️  跳过API密钥设置，AI功能可能无法正常工作")
    
    # 设置默认环境变量
    default_vars = {
        'DATABASE_URL': 'sqlite:///recordings.db',
        'UPLOAD_DIR': 'uploads',
        'PORT': '26000',
        'HOST': '0.0.0.0',
        'LOG_LEVEL': 'info'
    }
    
    for key, default_value in default_vars.items():
        if key not in os.environ:
            os.environ[key] = default_value


def check_dependencies():
    """检查依赖包"""
    print("📦 正在检查依赖包...")
    
    required_packages = [
        'fastapi', 'uvicorn', 'dashscope', 'sqlalchemy', 
        'jieba', 'soundfile', 'numpy', 'aiofiles'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        print("💡 请运行以下命令安装依赖:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    else:
        print("✅ 所有依赖包已安装")
        return True


def create_directories():
    """创建必要的目录"""
    print("📁 正在创建必要目录...")
    
    directories = ['uploads', 'logs']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ 目录已创建: {directory}")


def main():
    """主函数"""
    print("🚀 山源听悟 - AI语音识别平台启动器")
    print("=" * 50)
    
    # 1. 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 2. 设置环境变量
    setup_environment()
    
    # 3. 创建目录
    create_directories()
    
    # 4. 检查API密钥
    api_key = os.environ.get('DASHSCOPE_API_KEY')
    if not api_key or api_key == 'your_dashscope_api_key_here':
        print("⚠️  警告: 未设置有效的DashScope API密钥")
        print("💡 AI功能(智能摘要、关键词提取)将无法使用")
        print("💡 实时转写功能仍可正常使用")
        
        choice = input("是否继续启动? (y/N): ").strip().lower()
        if choice not in ['y', 'yes']:
            print("🛑 启动已取消")
            sys.exit(0)
    else:
        print("✅ DashScope API密钥已配置")
    
    print("=" * 50)
    print("🌟 正在启动服务器...")
    print(f"📍 服务地址: http://{os.environ.get('HOST', '0.0.0.0')}:{os.environ.get('PORT', '26000')}")
    print(f"🔗 WebSocket: ws://{os.environ.get('HOST', '0.0.0.0')}:{os.environ.get('PORT', '26000')}/ws/transcribe")
    print("💡 按 Ctrl+C 停止服务")
    print("=" * 50)
    
    # 5. 启动服务
    try:
        import uvicorn
        from main import app
        
        uvicorn.run(
            app,
            host=os.environ.get('HOST', '0.0.0.0'),
            port=int(os.environ.get('PORT', 26000)),
            log_level=os.environ.get('LOG_LEVEL', 'info').lower()
        )
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 服务启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 