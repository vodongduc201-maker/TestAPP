import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Báo Cáo MT Chương Dương - v4026", page_icon="🥤", layout="centered")

# --- 2. CSS CUSTOM (BOXED UI & AUTO THEME) ---
st.markdown("""
    <style>
    /* Bo góc và đổ bóng nhẹ cho các ô nhập liệu */
    .stSelectbox, .stNumberInput, .stTextArea, .stTextInput {
        background-color: var(--secondary-bg-color);
        padding: 8px;
        border-radius: 10px;
        border: 1px solid rgba(128, 128, 128, 0.1);
    }
    /* Khung bao quanh từng sản phẩm */
    .product-box {
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 12px;
        border-radius: 15px;
        margin-bottom: 12px;
        background-color: var(--background-color);
        box-shadow: 0px 2px 8px rgba(0, 0, 0, 0.05);
    }
    /* Tiêu đề sản phẩm có vạch đỏ bên trái */
    .product-header {
        background-color: var(--secondary-bg-color);
        color: var(--text-color);
        padding: 6px 12px;
        border-radius: 8px;
        border-left: 5px solid #ff4b4b;
        font-weight: bold;
        font-size: 14px;
        margin-bottom: 10px;
    }
    /* Nút bấm lớn, nổi bật */
    .stButton button {
        width: 100%;
        height: 55px;
        background-color: #ff4b4b !important;
        color: white !important;
        font-weight: bold;
        border-radius: 15px;
        box-shadow: 0px 4px 10px rgba(255, 75, 75, 0.3);
        margin-top: 20px;
    }
    .stCaption { text-align: center; font-size: 11px !important; margin-top: -5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. KẾT NỐI & THỜI GIAN ---
tz = pytz.timezone('Asia/Ho_Chi_Minh')
now = datetime.now(tz)
today_str = now.strftime("%d/%m/%Y")
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_append_to_sheets(rows_list):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["connections"]["gsheets"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Data_Bao_Cao_MT").worksheet("Data_Bao_Cao_MT")
        sheet.append_rows(rows_list)
        return True
    except Exception as e:
        st.error(f"❌ Lỗi ghi dữ liệu: {e}")
        return False

# --- 4. LOAD MASTER DATA ---
@st.cache_data(ttl=600)
def load_master():
    try:
        df = pd.read_excel("data nhan vien.xlsx", header=None)
        df = df.iloc[:, :4] 
        df.columns = ['NHAN VIEN', 'HE THONG', 'PHUONG', 'SIEU THI']
        return df.apply(lambda x: x.astype(str).str.strip())
    except: return None

df_master = load_master()
st.title("🥤 Báo Cáo MT Chương Dương")

if df_master is not None:
    list_nv = ["Chọn nhân viên..."] + sorted(df_master['NHAN VIEN'].unique().tolist())
    sel_nv = st.selectbox("👤 1. Nhân viên", options=list_nv)

    if sel_nv != "Chọn nhân viên...":
        try:
            df_history = conn.read(worksheet="Data_Bao_Cao_MT", ttl=0)
            if not df_history.empty:
                df_history['NGAY_DT'] = pd.to_datetime(df_history['NGAY'], format='%d/%m/%Y', errors='coerce')
        except: df_history = pd.DataFrame()

        st.divider()
        df_f1 = df_master[df_master['NHAN VIEN'] == sel_nv]
        c1, c2 = st.columns(2)
        with c1:
            sel_ht = st.selectbox("🏢 Hệ thống", options=sorted(df_f1['HE THONG'].unique().tolist()))
        with c2:
            sel_st = st.selectbox("📍 Siêu thị", options=sorted(df_f1[df_f1['HE THONG'] == sel_ht]['SIEU THI'].unique().tolist()))

        # --- 5. PHÂN LOẠI SẢN PHẨM THEO HỆ THỐNG (CẬP NHẬT CHUẨN) ---
        ht_up = sel_ht.upper()
        if ht_up == "CTY":
            list_sp = []
            st.info("🏢 Chế độ check-in Công ty: Chỉ nhập Ghi chú & Hình ảnh.")
        elif ht_up in ["SH", "BHX"]: 
            list_sp = ["Sa Xi Lon"]
        elif ht_up in ["B'SMART", "GS25"]: 
            list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390"]
        elif ht_up in ["EMART", "CS", "CM", "CF", "FL", "XTRA"]: 
            list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L"]
        else: 
            list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L", "Soda Kem Lon", "Suoi 500mL", "Soda Lon"]

        # Logic chặn
        history_st = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['SIEU THI'] == sel_st)] if not df_history.empty else pd.DataFrame()
        so_lan_thang = history_st[history_st['NGAY_DT'].dt.month == now.month]['NGAY'].nunique()
        UU_TIEN = ['CM', 'SF', 'CF', 'MM', 'GO!', 'EMART', 'CTY', 'SM', 'XTRA']
        is_blocked = (ht_up not in UU_TIEN and (so_lan_thang >= 2 or now.day > 21)) or \
                     (ht_up != 'CTY' and (now.hour * 60 + now.minute) >= (17 * 60 + 10))

        # --- 6. FORM NHẬP LIỆU BOXED ---
        with st.form("main_form", clear_on_submit=True):
            inputs = {}
            for sp in list_sp:
                st.markdown(f'<div class="product-box"><div class="product-header">{sp}</div>', unsafe_allow_html=True)
                col1, col2, col3 = st.columns(3)
                with col1:
                    f = st.number_input("F", 0, key=f"f_{sp}", label_visibility="collapsed")
                    st.caption("Facing")
                with col2:
                    t = st.number_input("T", 0, key=f"t_{sp}", label_visibility="collapsed")
                    st.caption("Thùng")
                with col3:
                    qc = 12 if "1.5L" in sp else 24
                    l = st.number_input("L", 0, qc-1, key=f"l_{sp}", label_visibility="collapsed")
                    st.caption("Lẻ")
                st.markdown('</div>', unsafe_allow_html=True)
                inputs[sp] = {"fc": f, "tk": (t * qc) + l}
            
            img = st.text_input("🔗 Link hình ảnh")
            note = st.text_area("💬 Ghi chú")

            btn_label = "🚀 GỬI BÁO CÁO"
            if is_blocked: btn_label = "🚫 ĐÃ KHÓA BÁO CÁO"

            if st.form_submit_button(btn_label, disabled=is_blocked):
                p = df_f1[df_f1['SIEU THI'] == sel_st]['PHUONG'].values[0]
                final_rows = []
                if ht_up == "CTY":
                    final_rows.append([today_str, now.strftime("%H:%M:%S"), sel_nv, sel_ht, p, sel_st, "Check-in CTY", 0, 0, note, img])
                else:
                    for s, v in inputs.items():
                        if v['fc'] > 0 or v['tk'] > 0:
                            final_rows.append([today_str, now.strftime("%H:%M:%S"), sel_nv, sel_ht, p, sel_st, s, v['fc'], v['tk'], note, img])
                
                if final_rows and safe_append_to_sheets(final_rows):
                    st.success("✅ Thành công!"); st.rerun()
