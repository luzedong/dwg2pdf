# PDF布局提取器 Web应用

这是一个基于Streamlit的PDF布局提取器Web应用，可以自动检测PDF中的布局区域并将其分离为独立的PDF页面。

## 功能特点

- 🔍 **智能检测**: 使用OpenCV自动检测PDF中的大矩形布局区域
- 🔄 **自动旋转**: 智能处理PDF方向，确保输出方向正确
- 📊 **可视化**: 提供检测结果的可视化预览
- 📦 **批量下载**: 支持单独下载或打包下载所有结果文件
- ⚙️ **参数调节**: 可调节DPI和图片尺寸等处理参数
- 🌐 **Web界面**: 友好的用户界面，支持拖拽上传

## 安装和运行

1. 安装依赖包：
```bash
pip install -r requirements.txt
```

2. 运行应用：
```bash
streamlit run pdf_layout_extractor_app.py
```

3. 在浏览器中打开显示的地址（通常是 http://localhost:8501）

## 使用方法

1. **上传PDF文件**: 点击上传区域或拖拽PDF文件
2. **调整参数**（可选）:
   - DPI设置: 影响检测精度，值越高精度越高但处理时间更长
   - 最大图片边长: 限制处理图片尺寸，避免内存溢出
3. **开始处理**: 点击"开始处理"按钮
4. **查看结果**: 查看检测到的矩形区域预览
5. **下载文件**: 下载分离后的PDF、检测结果图片或打包文件

## 技术栈

- **Streamlit**: Web应用框架
- **PyMuPDF**: PDF处理
- **pdf2image**: PDF转图片
- **OpenCV**: 图像处理和矩形检测
- **Pillow**: 图片处理
- **NumPy**: 数值计算

## 部署说明

### 本地部署
直接运行上述命令即可在本地启动应用。

### 云端部署
可以部署到以下平台：
- Streamlit Cloud
- Heroku
- AWS/Azure/GCP
- Docker容器

### Docker部署
创建Dockerfile：
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements_web.txt .
RUN pip install -r requirements.txt

COPY pdf_layout_extractor_app.py .

EXPOSE 8501

CMD ["streamlit", "run", "pdf_layout_extractor_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## 注意事项

- 确保PDF文件包含清晰的矩形边界
- 处理大文件时可能需要较长时间
- 建议使用现代浏览器以获得最佳体验
- 上传的文件会在处理后自动清理，不会保存在服务器上

## 故障排除

1. **检测不到矩形**: 尝试调整DPI参数或检查PDF质量
2. **内存不足**: 减小最大图片边长参数
3. **处理时间过长**: 降低DPI设置或处理较小的文件
4. **上传失败**: 检查文件格式是否为PDF且文件未损坏