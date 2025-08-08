import os
import tempfile
import streamlit as st
import fitz  # PyMuPDF
from pdf2image import convert_from_path
from PIL import Image
import cv2
import numpy as np
import zipfile
from io import BytesIO

def process_pdf_layout_extraction(pdf_file, dpi=30, max_side=100000):
    """
    处理PDF布局提取的主函数
    """
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        # 保存上传的PDF文件
        pdf_path = os.path.join(temp_dir, "input.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_file.read())
        
        # 重置文件指针
        pdf_file.seek(0)
        
        # 1. 读取PDF第一页尺寸和rotation
        doc = fitz.open(pdf_path)
        page = doc[0]
        pdf_w_pt = page.rect.width
        pdf_h_pt = page.rect.height
        rotation = page.rotation  # 0, 90, 180, 270
        doc.close()
        
        # 2. 计算图片像素尺寸（用dpi参数，保证比例）
        inch_per_pt = 1 / 72
        pdf_w_inch = pdf_w_pt * inch_per_pt
        pdf_h_inch = pdf_h_pt * inch_per_pt
        img_w = int(pdf_w_inch * dpi)
        img_h = int(pdf_h_inch * dpi)
        
        st.info(f"PDF页面尺寸: {pdf_w_pt:.2f}pt x {pdf_h_pt:.2f}pt, rotation: {rotation}")
        st.info(f"输出图片像素: {img_w} x {img_h}")
        
        # 3. 控制图片最大尺寸，防止超大
        if img_w > max_side or img_h > max_side:
            scale = max(img_w, img_h) / max_side
            img_w = int(img_w / scale)
            img_h = int(img_h / scale)
            st.info(f"缩放后图片像素: {img_w} x {img_h}")
        
        # 4. PDF转PNG（用dpi参数，保证比例）
        with st.spinner("正在转换PDF为图片..."):
            images = convert_from_path(pdf_path, dpi=dpi)
            img = images[0]
        
        # 5. 自动处理方向，保证和PDF页面一致
        if pdf_w_pt >= pdf_h_pt and img.width < img.height:
            img = img.rotate(-90, expand=True)
            st.info("图片已自动旋转-90度，保证和PDF方向一致。")
        elif pdf_w_pt < pdf_h_pt and img.width > img.height:
            img = img.rotate(90, expand=True)
            st.info("图片已自动旋转90度，保证和PDF方向一致。")
        
        img_path = os.path.join(temp_dir, "temp.png")
        img.save(img_path)
        
        # 6. OpenCV检测大矩形
        with st.spinner("正在检测大矩形..."):
            img_cv = cv2.imread(img_path)
            img_h, img_w = img_cv.shape[:2]
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blur, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        rects = []
        min_w, min_h = img_w // 20, img_h // 3
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w > min_w and h > min_h:
                rects.append((x, y, w, h))
        
        # 7. 只保留最外层大矩形
        rects = sorted(rects, key=lambda r: r[2]*r[3], reverse=True)
        
        def is_inside(inner, outer):
            x1, y1, w1, h1 = inner
            x2, y2, w2, h2 = outer
            return (x1 >= x2 and y1 >= y2 and
                    x1 + w1 <= x2 + w2 and
                    y1 + h1 <= y2 + h2)
        
        filtered_rects = []
        for i, rect in enumerate(rects):
            inside = False
            for j, other in enumerate(rects):
                if i != j and is_inside(rect, other):
                    inside = True
                    break
            if not inside:
                filtered_rects.append(rect)
        
        filtered_rects = sorted(filtered_rects, key=lambda r: r[0])
        
        # 8. 可视化检测结果
        img_rects = img_cv.copy()
        for (x, y, w, h) in filtered_rects:
            cv2.rectangle(img_rects, (x, y), (x + w, y + h), (0, 255, 0), 5)
        
        # 保存检测结果图片
        detected_img_path = os.path.join(temp_dir, 'detected_rects.png')
        cv2.imwrite(detected_img_path, img_rects)
        
        st.success(f"检测到 {len(filtered_rects)} 个大矩形（已去除嵌套）。")
        
        # 显示检测结果
        st.subheader("检测结果预览")
        st.image(detected_img_path, caption="检测到的矩形区域（绿色框）", use_column_width=True)
        
        if len(filtered_rects) == 0:
            st.warning("未检测到符合条件的矩形区域，请尝试调整参数。")
            return None, None
        
        # 9. 坐标映射到PDF单位并裁剪PDF
        with st.spinner("正在裁剪PDF..."):
            doc = fitz.open(pdf_path)
            page = doc[0]
            pdf_w, pdf_h = page.rect.width, page.rect.height
            scale_x = pdf_w / img_w
            scale_y = pdf_h / img_h
            
            output_pdf = fitz.open()
            for i, (x, y, w, h) in enumerate(filtered_rects):
                pdf_x0 = x * scale_x
                pdf_y0 = y * scale_y
                pdf_x1 = (x + w) * scale_x
                pdf_y1 = (y + h) * scale_y
                rect = fitz.Rect(pdf_x0, pdf_y0, pdf_x1, pdf_y1)
                new_page = output_pdf.new_page(width=rect.width, height=rect.height)
                new_page.show_pdf_page(new_page.rect, doc, 0, clip=rect)
            
            # 10. 保存新PDF到内存
            pdf_bytes = output_pdf.tobytes()
            output_pdf.close()
            doc.close()
        
        # 读取检测结果图片到内存
        with open(detected_img_path, 'rb') as f:
            img_bytes = f.read()
        
        return pdf_bytes, img_bytes

def create_download_zip(pdf_bytes, img_bytes):
    """创建包含PDF和检测图片的ZIP文件"""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("split_layouts.pdf", pdf_bytes)
        zip_file.writestr("detected_rects.png", img_bytes)
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def main():
    st.set_page_config(
        page_title="PDF布局提取器",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("📄 PDF布局提取器")
    st.markdown("---")
    
    # 侧边栏参数设置
    st.sidebar.header("⚙️ 参数设置")
    dpi = st.sidebar.slider(
        "DPI设置", 
        min_value=20, 
        max_value=100, 
        value=30, 
        step=5,
        help="较高的DPI会提高检测精度，但处理时间更长"
    )
    
    max_side = st.sidebar.slider(
        "最大图片边长", 
        min_value=5000, 
        max_value=200000, 
        value=100000, 
        step=5000,
        help="限制处理图片的最大尺寸，避免内存溢出"
    )
    
    # 主界面
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📁 文件上传")
        uploaded_file = st.file_uploader(
            "选择PDF文件",
            type=['pdf'],
            help="上传包含多个布局的PDF文件"
        )
    
    with col2:
        st.subheader("ℹ️ 使用说明")
        st.markdown("""
        1. 上传包含多个布局的PDF文件
        2. 调整侧边栏中的参数（可选）
        3. 点击"开始处理"按钮
        4. 查看检测结果并下载文件
        
        **注意：** 
        - 支持自动旋转和方向调整
        - 会自动过滤嵌套的矩形区域
        - 输出包含分离后的各个布局
        """)
    
    if uploaded_file is not None:
        st.markdown("---")
        
        # 显示文件信息
        file_details = {
            "文件名": uploaded_file.name,
            "文件大小": f"{uploaded_file.size / 1024 / 1024:.2f} MB",
            "文件类型": uploaded_file.type
        }
        
        st.subheader("📋 文件信息")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("文件名", file_details["文件名"])
        with col2:
            st.metric("文件大小", file_details["文件大小"])
        with col3:
            st.metric("文件类型", file_details["文件类型"])
        
        st.markdown("---")
        
        # 处理按钮
        if st.button("🚀 开始处理", type="primary", use_container_width=True):
            try:
                # 处理PDF
                pdf_bytes, img_bytes = process_pdf_layout_extraction(
                    uploaded_file, 
                    dpi=dpi, 
                    max_side=max_side
                )
                
                if pdf_bytes is not None and img_bytes is not None:
                    st.markdown("---")
                    st.subheader("📥 下载结果")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.download_button(
                            label="📄 下载分离后的PDF",
                            data=pdf_bytes,
                            file_name="split_layouts.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    
                    with col2:
                        st.download_button(
                            label="🖼️ 下载检测结果图片",
                            data=img_bytes,
                            file_name="detected_rects.png",
                            mime="image/png",
                            use_container_width=True
                        )
                    
                    with col3:
                        zip_bytes = create_download_zip(pdf_bytes, img_bytes)
                        st.download_button(
                            label="📦 下载全部文件(ZIP)",
                            data=zip_bytes,
                            file_name="layout_extraction_results.zip",
                            mime="application/zip",
                            use_container_width=True
                        )
                    
                    st.success("✅ 处理完成！您可以下载结果文件。")
                    
            except Exception as e:
                st.error(f"❌ 处理过程中出现错误: {str(e)}")
                st.info("请尝试调整参数或检查PDF文件格式。")
    
    else:
        st.info("👆 请上传一个PDF文件开始处理")
    
    # 页脚
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>PDF布局提取器 | 基于OpenCV和PyMuPDF技术</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()