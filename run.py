#!/usr/bin/env python3
"""
S3 API 文件管理器启动脚本
"""

import sys
import os
from pathlib import Path

def check_dependencies():
    """检查必要的依赖包"""
    required_packages = ['boto3', 'tkinterdnd2']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("缺少以下必要的依赖包:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n请运行以下命令安装依赖:")
        print("pip install -r requirements.txt")
        return False
    
    return True

def load_env_file():
    """加载.env文件"""
    env_file = Path('.env')
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("已加载 .env 配置文件")
        except ImportError:
            print("提示: 安装 python-dotenv 可自动加载 .env 文件")
    else:
        print("提示: 可以创建 .env 文件来配置S3连接信息")
        print("参考 .env.example 文件格式")

def main():
    """主函数"""
    print("S3 文件管理器启动中...")
    
    if not check_dependencies():
        sys.exit(1)
    
    load_env_file()
    
    try:
        from main_gui import S3GUI
        app = S3GUI()
        app.run()
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()