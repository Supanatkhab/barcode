# 1. ใช้ base image Python 3.13
FROM python:3.13-slim

# 2. ติดตั้ง system libraries ที่ pyzbar ต้องการ
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libzbar0 \
        libzbar-dev \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

# 3. สร้าง working directory
WORKDIR /app

# 4. คัดลอกไฟล์ requirements.txt
COPY requirements.txt .

# 5. ติดตั้ง Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 6. คัดลอกโค้ดโปรเจกต์ทั้งหมด
COPY . .

# 7. เปิด port สำหรับ Streamlit
EXPOSE 8501

# 8. รัน Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
