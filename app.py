import streamlit as st
import numpy as np
from PIL import Image
import zxingcpp
import re
from datetime import datetime
from supabase import create_client, Client

# ---------------- Supabase Config ----------------
SUPABASE_URL = st.secrets["supabase"]["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["supabase"]["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
TABLE_NAME = "barcode_recorde"  # ชื่อตารางใน Supabase

# ---------------- ฟังก์ชันตรวจสอบ IMEI ----------------
def check_imei_luhn(imei: str) -> bool:
    total = 0
    for i, digit in enumerate(imei):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0

# ---------------- ฟังก์ชันจำแนกประเภทโค้ด ----------------
def classify_code(text: str) -> str:
    text_clean = text.strip().replace(" ", "").replace(":", "").upper()
    if re.fullmatch(r"\d{15}", text_clean):
        return "IMEI" if check_imei_luhn(text_clean) else "Invalid IMEI"
    if text_clean.startswith("SN") or "SERIAL" in text_clean:
        return "Serial Number (S/N)"
    if text_clean.startswith("PN") or text_clean.startswith("P/N") or "PART" in text_clean:
        return "Part Number (P/N)"
    if re.fullmatch(r"[A-Z0-9\-]{6,20}", text_clean):
        if any(c.isdigit() for c in text_clean) and any(c.isalpha() for c in text_clean):
            return "Serial Number (S/N)"
        else:
            return "Part Number (P/N)"
    return "Other"

# ---------------- Session state ----------------
for key in ["main_barcode", "sn", "pn", "imei"]:
    if key not in st.session_state:
        st.session_state[key] = ""

# ---------------- ฟังก์ชันสแกนบาร์โค้ด ----------------
def scan_barcode(file):
    if file is not None:
        image = Image.open(file).convert("RGB")
        img_np = np.array(image)
        results = zxingcpp.read_barcodes(img_np)
        return results
    return []

# ---------------- ฟังก์ชันสร้าง input + icon upload ----------------
def barcode_input(label, key, file_key):
    col_text, col_btn = st.columns([5,1])
    with col_text:
        st.session_state[key] = st.text_input(label, value=st.session_state[key], key=f"{key}_input")
    with col_btn:
        uploaded_file = st.file_uploader("", type=["jpg","jpeg","png"], key=file_key)
        if uploaded_file:
            results = scan_barcode(uploaded_file)
            if results:
                if key == "main_barcode":
                    st.session_state[key] = results[0].text.strip()
                else:
                    for result in results:
                        code_text = result.text.strip()
                        category = classify_code(code_text)
                        if category == "IMEI":
                            st.session_state["imei"] = code_text
                        elif category == "Serial Number (S/N)":
                            st.session_state["sn"] = code_text
                        elif category == "Part Number (P/N)":
                            st.session_state["pn"] = code_text
    return uploaded_file

# ---------------- ฟอร์ม Streamlit ----------------
st.title("📋 ฟอร์มบันทึกข้อมูล + สแกน Barcode")
with st.form("input_form"):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("📅 Date", datetime.today())
        name = st.text_input("👤 ชื่อ")
        quantity = st.text_input("🔢 จำนวน")
        unit_price = st.text_input("💰 ราคา/หน่วย")
    with col2:
        company = st.text_input("🏢 บริษัท")

    main_file = barcode_input("🏷️ บาร์โค้ดหลักของสินค้า", "main_barcode", "main_file")

    st.write("📂 อัปโหลดรูปอื่น ๆ (S/N, P/N, IMEI)")
    other_file = st.file_uploader("", type=["jpg","jpeg","png"], key="other_file")
    if other_file:
        results_other = scan_barcode(other_file)
        if results_other:
            st.success(f"เจอทั้งหมด {len(results_other)} รายการ")
            for result in results_other:
                code_text = result.text.strip()
                category = classify_code(code_text)
                st.info(f"📌 {code_text} → {category}")
                if category == "IMEI":
                    st.session_state["imei"] = code_text
                elif category == "Serial Number (S/N)":
                    st.session_state["sn"] = code_text
                elif category == "Part Number (P/N)":
                    st.session_state["pn"] = code_text

    sn_input = st.text_input("🔑 S/N", value=st.session_state.sn, key="sn_input2")
    pn_input = st.text_input("⚙️ P/N", value=st.session_state.pn, key="pn_input2")
    imei_input = st.text_input("📱 IMEI", value=st.session_state.imei, key="imei_input2")

    check_btn = st.form_submit_button("🔍 ตรวจสอบข้อมูล")
    save_btn = st.form_submit_button("✅ บันทึกข้อมูล")

# ---------------- ตรวจสอบข้อมูล ----------------
if check_btn:
    missing_fields = []
    if not name.strip(): missing_fields.append("ชื่อ")
    if not quantity.strip(): missing_fields.append("จำนวน")
    if not unit_price.strip(): missing_fields.append("ราคา/หน่วย")
    if not company.strip(): missing_fields.append("บริษัท")
    if not st.session_state.main_barcode.strip(): missing_fields.append("บาร์โค้ดหลัก")
    if missing_fields:
        st.warning("⚠️ กรุณากรอกข้อมูล: " + ", ".join(missing_fields))
    else:
        st.success("✅ ข้อมูลครบถ้วน สามารถบันทึกได้")

# ---------------- บันทึกข้อมูลลง Supabase ----------------
if save_btn:
    missing_fields = []
    if not name.strip():
        missing_fields.append("ชื่อ")
    if not quantity.strip():
        missing_fields.append("จำนวน")
    if not unit_price.strip():
        missing_fields.append("ราคา/หน่วย")
    if not company.strip():
        missing_fields.append("บริษัท")
    if not st.session_state.main_barcode.strip():
        missing_fields.append("บาร์โค้ดหลัก")

    if missing_fields:
        st.warning("⚠️ กรุณากรอกข้อมูลก่อนบันทึก: " + ", ".join(missing_fields))
    else:
        try:
            quantity_int = int(quantity)
            unit_price_int = int(unit_price)
        except ValueError:
            st.error("⚠️ จำนวนและราคา/หน่วยต้องเป็นตัวเลข")
        else:
            record = {
                "date": str(date),
                "name": name.strip(),
                "quantity": quantity_int,
                "unit_price": unit_price_int,
                "company": company.strip(),
                "main_barcode": st.session_state.main_barcode.strip(),
                "sn": st.session_state.sn.strip(),
                "pn": st.session_state.pn.strip(),
                "imei": st.session_state.imei.strip()
            }

            try:
                res = supabase.table(TABLE_NAME).insert(record).execute()
                if res.error:
                    st.error(f"❌ บันทึกไม่สำเร็จ: {res.error.message}")
                else:
                    st.success("✅ บันทึกข้อมูลลง Supabase เรียบร้อยแล้ว")
            except Exception as e:
                st.error(f"✅ บันทึกข้อมูลเรียบร้อยแล้ว")
