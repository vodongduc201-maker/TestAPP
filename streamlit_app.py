import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Báo Cáo MT Chương Dương - v4026", page_icon="🥤", layout="centered")

# --- 2. CSS THÔNG MINH (BOXED UI) ---
st.markdown("""
    <style>
    /* Tổng thể khung bao ngoài cho từng section */
    .stSelectbox, .stNumberInput, .stTextArea, .stTextInput {
        background-color: var(--secondary-bg-color);
        padding: 10px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 5px;
    }
    
    /* Đóng khung từng sản phẩm */
    .product-box {
        border: 1px solid var(--secondary-bg-color);
        background-color: var(--background-color);
        padding: 12px;
        border-radius: 15px;
        margin-bottom: 15px;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.05);
    }

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

    /* Tối ưu cột cho mobile */
    [data-testid="column"] {
        padding: 0px 2px !important;
    }

    /* Nút bấm lớn */
    .stButton button {
        width: 100%;
        height: 55px;
        background-color: #ff4b4b !important;
        color: white !important;
        font-weight: bold;
        border-radius: 15px;
        border: none;
        box-shadow: 0px 4px 15px rgba(255, 75, 75, 0.4);
        margin-top: 20px;
    }
    
    /* Chỉnh caption nhỏ lại cho tinh tế */
    .stCaption {
        text-align: center;
        font-size: 10px !important;
        margin-top: -5px;
    }
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
        for row in rows_list:
            values = [row.get("NGAY"), row.get("GIO"), row.get("NHAN VIEN"), 
                      row.get("HE THONG"), row.get("PHUONG"), row.get("SIEU THI"), 
                      row.get("SAN PHAM"), row.get("FACING"), row.get("TON KHO"), 
                      row.get("GHI CHU"), row.get("HINH ANH")]
            sheet.append_row(values)
        return True
    except Exception as e:
        st.error(f"❌ Lỗi ghi dữ liệu: {e}")
        return False

UU_TIEN_LIST = ['CM', 'SF', 'CF', 'MM', 'GO!', 'emart', 'CTY', 'SM', 'XTRA']

@st.cache_data(ttl=0)
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
    sel_nv = st.selectbox("👤 Bước 1: Nhân viên", options=list_nv)

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

        ht_up = sel_ht.upper()
        user_today = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['NGAY'] == today_str)] if not df_history.empty else pd.DataFrame()

        # Nhật ký
        if not user_today.empty:
            with st.expander("🕒 Nhật ký viếng thăm hôm nay", expanded=False):
                log_v = user_today[['GIO', 'SIEU THI']].sort_values(by='GIO', ascending=False).drop_duplicates(subset=['SIEU THI'])
                st.table(log_v)

        # Nhắc lịch
        if sel_st and ht_up != "CTY":
            history_st = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['SIEU THI'] == sel_st)] if not df_history.empty else pd.DataFrame()
            so_lan_thang = history_st[history_st['NGAY_DT'].dt.month == now.month]['NGAY'].nunique()
            last_visit = history_st['NGAY_DT'].max() if not history_st.empty else None
            
            if pd.notnull(last_visit):
                st.info(f"🕒 Ghé lần cuối: {last_visit.strftime('%d/%m/%Y')} ({so_lan_thang} lần/tháng)")
                if ht_up not in UU_TIEN_LIST and so_lan_thang == 1:
                    st.warning("⚠️ LƯU Ý: Đây là lần cuối của tháng!")
            else: st.success("✨ Điểm mới hoàn toàn!")

        # Logic chặn
        is_blocked = (ht_up not in UU_TIEN_LIST and (so_lan_thang >= 2 or now.day > 21)) or \
                     (ht_up != 'CTY' and (now.hour * 60 + now.minute) >= (17 * 60 + 10))
        
        wait_s = 0
        if not user_today.empty:
            diff = (now - tz.localize(datetime.strptime(f"{today_str} {user_today.iloc[-1]['GIO']}", "%d/%m/%Y %H:%M:%S"))).total_seconds()
            if diff < 120: wait_s = int(120 - diff)

        # Danh mục sản phẩm
        if ht_up == "CTY": list_sp = []
        elif ht_up in ["SH", "BHX"]: list_sp = ["Sa Xi Lon"]
        elif ht_up in ["B'SMART", "GS25"]: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390"]
        else: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L", "Soda Kem Lon", "Suoi 500mL", "Soda Lon"]

        # Form nhập liệu
        with st.form("boxed_form", clear_on_submit=True):
            inputs = {}
            for sp in list_sp:
                # Mỗi sản phẩm nằm trong 1 cái box riêng
                st.markdown(f'<div class="product-box"><div class="product-header">{sp}</div>', unsafe_allow_html=True)
                col1, col2, col3 = st.columns(3)
                with col1:
                    f = st.number_input("Facing", 0, key=f"f_{sp}", label_visibility="collapsed")
                    st.caption("Facing")
                with col2:
                    t = st.number_input("Thùng", 0, key=f"t_{sp}", label_visibility="collapsed")
                    st.caption("Thùng")
                with col3:
                    qc = 12 if "1.5L" in sp else 24
                    l = st.number_input("Lẻ", 0, qc-1, key=f"l_{sp}", label_visibility="collapsed")
                    st.caption("Lẻ")
                st.markdown('</div>', unsafe_allow_html=True)
                inputs[sp] = {"fc": f, "tk": (t * qc) + l}
            
            st.write("---")
            img = st.text_input("🔗 Link hình ảnh")
            note = st.text_area("💬 Ghi chú")

            btn_label = "🚀 GỬI BÁO CÁO"
            if is_blocked: btn_label = "🚫 ĐÃ KHÓA BÁO CÁO"
            elif wait_s > 0: btn_label = f"⏳ ĐỢI {wait_s}s..."

            if st.form_submit_button(btn_label, disabled=(is_blocked or wait_s > 0)):
                p = df_f1[df_f1['SIEU THI'] == sel_st]['PHUONG'].values[0]
                if ht_up == "CTY":
                    rows = [{"NGAY": today_str, "GIO": now.strftime("%H:%M:%S"), "NHAN VIEN": sel_nv, "HE THONG": sel_ht, "PHUONG": p, "SIEU THI": sel_st, "SAN PHAM": "Check-in CTY", "FACING": 0, "TON KHO": 0, "GHI CHU": note, "HINH ANH": img}]
                else:
                    rows = [{"NGAY": today_str, "GIO": now.strftime("%H:%M:%S"), "NHAN VIEN": sel_nv, "HE THONG": sel_ht, "PHUONG": p, "SIEU THI": sel_st, "SAN PHAM": s, "FACING": v['fc'], "TON KHO": v['tk'], "GHI CHU": note, "HINH ANH": img} for s, v in inputs.items() if v['fc'] > 0 or v['tk'] > 0]
                if rows and safe_append_to_sheets(rows):
                    st.success("✅ Thành công!"); st.rerun()
