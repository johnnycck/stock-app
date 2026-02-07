import streamlit as st
import os
import glob
import whisper
import subprocess
from fpdf import FPDF
from datetime import datetime

# 設定頁面
st.set_page_config(page_title="股市分析生成器", layout="centered")
st.title("📱 股市影片轉 PDF 神器")
st.write("貼上網址 ➔ 雲端運算 ➔ 手機下載 PDF")

# --- 核心功能 ---
def install_font():
    # 每次雲端啟動時自動下載字型
    font_path = "NotoSansTC-Regular.otf"
    if not os.path.exists(font_path):
        url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf"
        subprocess.run(["curl", "-L", url, "-o", font_path])
    return font_path

class PDFReport(FPDF):
    def header(self):
        self.set_font('NotoSans', '', 10)
        self.cell(0, 10, 'Stock Analysis Report', 0, 1, 'R')

def generate_pdf(txt_path, screenshot_folder, output_pdf_path, font_path):
    pdf = PDFReport()
    pdf.add_font('NotoSans', '', font_path, uni=True)
    pdf.set_font("NotoSans", size=12)
    
    # 逐字稿
    pdf.add_page()
    pdf.set_font("NotoSans", size=16)
    pdf.cell(0, 10, "【逐字稿內容】", ln=True)
    pdf.ln(5)
    pdf.set_font("NotoSans", size=10)
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            for line in f:
                clean_line = line.strip().encode('utf-8', 'replace').decode('utf-8')
                if clean_line:
                    pdf.multi_cell(0, 6, clean_line)
    except: pass

    # 截圖
    pdf.add_page()
    pdf.set_font("NotoSans", size=14)
    pdf.cell(0, 10, "【關鍵截圖】", ln=True)
    pdf.ln(5)
    if os.path.exists(screenshot_folder):
        images = sorted(glob.glob(os.path.join(screenshot_folder, "*.jpg")))
        for i, img in enumerate(images):
            if i % 2 == 0 and i != 0: pdf.add_page()
            pdf.set_font("NotoSans", size=9)
            pdf.cell(0, 8, f"Time: {os.path.basename(img)}", ln=True)
            try:
                pdf.image(img, w=170)
                pdf.ln(2)
            except: pass
    pdf.output(output_pdf_path)

# --- 介面 ---
url = st.text_input("YouTube 網址")
interval = st.slider("截圖頻率 (秒)", 30, 120, 60)

if st.button("🚀 開始生成", type="primary"):
    if not url:
        st.error("請輸入網址")
    else:
        status = st.empty()
        bar = st.progress(0)
        
        # 1. 環境準備
        font_path = install_font()
        if not os.path.exists("downloads"): os.makedirs("downloads")
        
        # 2. 下載影片
        status.text("正在雲端下載影片...")
        bar.progress(20)
        subprocess.run([
            "yt-dlp", "-f", "worstvideo[height<=480]+bestaudio/best", 
            "--merge-output-format", "mp4", 
            "-o", "downloads/temp_video.%(ext)s", 
            "--no-playlist", url
        ])
        
        video_files = glob.glob("downloads/*.mp4")
        if not video_files:
            st.error("下載失敗")
        else:
            video_path = video_files[0]
            
            # 3. 轉錄 (使用 base 模型以節省雲端資源)
            status.text("AI 正在聽寫 (這需要一點時間)...")
            bar.progress(50)
            model = whisper.load_model("base") # Streamlit 免費版資源有限，用 base 比較穩
            result = model.transcribe(video_path, fp16=False)
            
            txt_path = "downloads/transcript.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                for s in result['segments']:
                    f.write(f"[{int(s['start'])//60}:{int(s['start'])%60:02d}] {s['text']}\n")
            
            # 4. 截圖
            status.text("正在擷取關鍵畫面...")
            bar.progress(80)
            img_dir = "downloads/screenshots"
            if not os.path.exists(img_dir): os.makedirs(img_dir)
            subprocess.run([
                'ffmpeg', '-i', video_path, '-vf', f'fps=1/{interval}', 
                f'{img_dir}/img_%03d.jpg', '-hide_banner', '-loglevel', 'error'
            ])
            
            # 5. 打包 PDF
            status.text("正在生成 PDF...")
            bar.progress(90)
            pdf_path = "downloads/Analysis_Report.pdf"
            generate_pdf(txt_path, img_dir, pdf_path, font_path)
            
            bar.progress(100)
            status.success("完成！")
            
            # 提供下載按鈕
            with open(pdf_path, "rb") as f:
                st.download_button("⬇️ 下載 PDF 報告", f, file_name="Stock_Report.pdf")