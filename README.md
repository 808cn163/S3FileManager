# S3FileManager
一个基于S3-API的远端文件管理客户端。使用于:AWS S3、Cloudflare R2、MinIO、腾讯云COS、阿里云OSS、其他S3兼容存储服务。

# S3 API 文件管理器
一个基于 Python 和 Tkinter 的 S3 兼容存储文件管理器，支持文件的上传、下载、浏览和管理功能。

## 功能特性

### 📁 文件上传
- **拖拽上传**: 支持直接拖拽文件或文件夹到界面进行上传
- **对话框上传**: 通过文件选择对话框选择单个文件或整个文件夹上传
- **批量上传**: 支持多文件同时上传，自动处理并发上传
- **进度显示**: 实时显示上传进度

### 🔍 文件浏览
- **目录导航**: 支持进入下级目录和返回上级目录
- **文件列表**: 清晰显示文件名、类型、大小和修改时间
- **排序功能**: 支持按文件名、类型、大小、修改时间排序
- **升序/降序**: 可切换排序方向

### 📥 文件下载  
- **单文件下载**: 选中单个文件进行下载
- **目录下载**: 支持整个文件夹的递归下载
- **进度显示**: 实时显示下载进度
- **自动创建目录**: 下载时自动创建本地目录结构

### 🗑️ 文件删除
- **单文件删除**: 删除选中的单个文件
- **目录删除**: 删除整个文件夹及其内容
- **批量删除**: 支持选择多个项目进行批量删除
- **确认对话框**: 删除前显示确认提示

### ⚙️ 配置管理
- **JSON配置**: 使用 `config.json` 存储应用配置
- **环境变量支持**: 支持从 `.env` 文件加载S3配置
- **可视化设置**: 通过GUI界面配置S3连接参数

## 安装和运行

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置S3连接
创建 `.env` 文件（参考 `.env.example`）：
```env
S3_ENDPOINT=https://your-endpoint.r2.cloudflarestorage.com
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_REGION=auto
```

### 3. 运行程序
```bash
python run.py
```

或直接运行主程序：
```bash
python main_gui.py
```

## 文件结构

```
s3-api/
├── config.json              # 应用配置文件（自动生成）
├── config_manager.py        # 配置管理模块
├── s3_client.py            # S3客户端模块
├── main_gui.py             # GUI主界面
├── run.py                  # 启动脚本
├── requirements.txt        # 依赖包列表
├── .env.example           # 环境变量配置示例
└── README.md              # 说明文档
```

## 配置说明

### config.json 结构
```json
{
  "s3_config": {
    "endpoint": "S3服务端点URL",
    "bucket": "存储桶名称",
    "access_key": "访问密钥",
    "secret_key": "秘密密钥",
    "region": "区域设置"
  },
  "app_settings": {
    "default_download_path": "./downloads",
    "max_concurrent_uploads": 5,
    "max_concurrent_downloads": 3,
    "chunk_size": 8388608,
    "auto_create_folders": true
  },
  "ui_settings": {
    "window_width": 1200,
    "window_height": 800,
    "theme": "light"
  }
}
```

### S3配置参数说明
- **endpoint**: S3服务的访问端点，如 Cloudflare R2、AWS S3等
- **bucket**: 要访问的存储桶名称
- **access_key**: S3访问密钥ID
- **secret_key**: S3秘密访问密钥
- **region**: 区域设置，通常设为 "auto"

## 使用说明

### 1. 首次使用
- 启动程序后，如果未配置S3连接，会自动打开设置对话框
- 填入S3连接信息后，点击"测试连接"验证配置
- 连接成功后保存设置

### 2. 文件上传
- **拖拽**: 直接将文件或文件夹拖拽到程序窗口
- **按钮**: 点击"上传文件"或"上传文件夹"按钮选择要上传的内容
- **菜单**: 通过"文件"菜单选择上传选项

### 3. 文件浏览
- 双击文件夹进入下级目录
- 使用"返回上级"按钮返回上级目录
- 通过排序选项按不同条件排列文件

### 4. 文件下载
- 选中要下载的文件或文件夹
- 点击"下载"按钮或使用右键菜单
- 选择本地保存目录

### 5. 文件删除
- 选中要删除的项目
- 点击"删除"按钮或使用右键菜单
- 确认删除操作

## 兼容性

### S3兼容服务
- AWS S3
- Cloudflare R2
- MinIO
- 腾讯云COS
- 阿里云OSS
- 其他S3兼容存储服务

### 系统要求
- Python 3.7+
- Windows/Linux/macOS
- GUI环境支持

## 注意事项

1. **网络连接**: 确保网络连接稳定，特别是上传/下载大文件时
2. **权限配置**: 确保S3访问密钥具有相应的读写权限
3. **文件名**: 避免使用特殊字符作为文件名
4. **并发限制**: 程序默认限制并发上传和下载数量，可通过配置调整

## 故障排除

### 常见问题

1. **连接失败**
   - 检查网络连接
   - 验证S3配置参数
   - 确认访问密钥权限

2. **上传/下载失败**
   - 检查文件权限
   - 确认存储桶权限
   - 检查磁盘空间

3. **界面无响应**
   - 文件操作在后台进行，请耐心等待
   - 查看状态栏进度提示

## 开发说明

### 核心模块
- `config_manager.py`: 负责配置文件的读取、写入和管理
- `s3_client.py`: 封装boto3客户端，提供S3操作接口
- `main_gui.py`: GUI界面和用户交互逻辑

### 扩展开发
程序采用模块化设计，可方便地扩展功能：
- 添加新的S3操作功能
- 定制GUI界面
- 集成其他云存储服务

## 打包成exe指南
## 解决 tkinterdnd2 打包问题
您遇到的问题是在打包过程中 tkinterdnd2 库的 tkdnd 包无法被正确加载。这是因为 PyInstaller 在打包时没有正确包含 tkinterdnd2 的二进制组件。下面是解决方案：

### 解决方案
方法一：手动添加 tkdnd 库文件
找到 tkinterdnd2 的安装位置

pip show tkinterdnd2
记下显示的 Location 路径。

创建一个自定义的 hook 文件

创建文件 hook-tkinterdnd2.py，内容如下：

# hook-tkinterdnd2.py
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files('tkinterdnd2')
hiddenimports = collect_submodules('tkinterdnd2')

修改 PyInstaller 命令
pyinstaller --onefile --windowed --additional-hooks-dir=. main_gui.py --name "S3FileManager"

pyinstaller --onefile --windowed --icon=cloudflare.ico --additional-hooks-dir=. main_gui.py --name "S3FileManager"

## 许可证

本项目采用 MIT 许可证。
