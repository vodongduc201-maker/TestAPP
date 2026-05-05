import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Báo Cáo MT Chương Dương - v4026", page_icon="🥤", layout="centered")

# --- 2. CSS CUSTOM (LÀM NHỎ GỌN NHẬP LIỆU) ---
st.markdown("""
    <style>
    /* Thu nhỏ khoảng cách giữa các thành phần */
    .stNumberInput {
        margin-bottom: -15px !important;
    }
    /* Làm tiêu đề sản phẩm nổi bật nhưng gọn */
    .product-header {
        background-color: #f0f2f6;
        padding: 5px 10px;
        border-radius: 5px;
        border-left: 5px solid #ff4b4b;
        font-weight: bold;
        margin-top: 10px;
        margin-bottom: 5px;
        font-size: 14px;
    }
    /* Tối ưu hóa bảng hiển thị */
    div[data-testid="stExpander"] {
        border: 1px solid #e6e9ef;
        border-radius: 8px;
    }
    /* Làm nút Gửi to và dễ bấm hơn */
    .stButton button {
        width: 100%;
        height: 50px;
        background-color: #ff4b4b;
        color: white;
        font-weight: bold;
        border-radius: 10px;
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
            sel_ht = st.selectbox("2. Hệ thống", options=sorted(df_f1['HE THONG'].unique().tolist()))
        with c2:
            sel_st = st.selectbox("3. Siêu thị", options=sorted(df_f1[df_f1['HE THONG'] == sel_ht]['SIEU THI'].unique().tolist()))

        ht_up = sel_ht.upper()
        user_today = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['NGAY'] == today_str)] if not df_history.empty else pd.DataFrame()

        # --- NHẬT KÝ VIẾNG THĂM ---
        if not user_today.empty:
            with st.expander("🕒 Nhật ký viếng thăm hôm nay", expanded=False):
                log_v = user_today[['GIO', 'SIEU THI']].sort_values(by='GIO', ascending=False).drop_duplicates(subset=['SIEU THI'])
                st.table(log_v)

        # --- NHẮC LỊCH & CẢNH BÁO ---
        if sel_st and ht_up != "CTY":
            history_st = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['SIEU THI'] == sel_st)] if not df_history.empty else pd.DataFrame()
            so_lan_thang = history_st[history_st['NGAY_DT'].dt.month == now.month]['NGAY'].nunique()
            last_visit = history_st['NGAY_DT'].max() if not history_st.empty else None
            
            if pd.notnull(last_visit):
                if (now.replace(tzinfo=None) - last_visit).days == 0:
                    st.info(f"📍 Hôm nay đã ghé. (Tổng: {so_lan_thang} lần/tháng)")
                else:
                    st.warning(f"🕒 Ghé lần cuối: {last_visit.strftime('%d/%m/%Y')}")
                
                if ht_up not in UU_TIEN_LIST and so_lan_thang == 1:
                    st.markdown('<p style="color:red; font-weight:bold;">⚠️ ĐÂY LÀ LẦN CUỐI CỦA THÁNG!</p>', unsafe_allow_html=True)
            else:
                st.success("✨ Điểm mới hoàn toàn!")

        # --- LOGIC CHẶN ---
        is_blocked = (ht_up not in UU_TIEN_LIST and (so_lan_thang >= 2 or now.day > 21)) or \
                     (ht_up != 'CTY' and (now.hour * 60 + now.minute) >= (17 * 60 + 10))
        
        wait_s = 0
        if not user_today.empty:
            diff = (now - tz.localize(datetime.strptime(f"{today_str} {user_today.iloc[-1]['GIO']}", "%d/%m/%Y %H:%M:%S"))).total_seconds()
            if diff < 120: wait_s = int(120 - diff)

        if is_blocked: st.error("🚫 Không thể báo cáo (Hết hạn mức/Sau 17:10/Sau ngày 21).")
        elif wait_s > 0: st.warning(f"⏳ Đợi {wait_s}s...")

        # --- PHẦN NHẬP LIỆU GỌN (DÙNG HTML/CSS HEADER) ---
        if ht_up == "CTY": list_sp = []
        elif ht_up in ["SH", "BHX"]: list_sp = ["Sa Xi Lon"]
        elif ht_up in ["B'SMART", "GS25"]: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390"]
        else: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L", "Soda Kem Lon", "Suoi 500mL", "Soda Lon"]

        with st.form("compact_form", clear_on_submit=True):
            inputs = {}
            for sp in list_sp:
                # Dùng HTML để tạo header sản phẩm nhỏ gọn
                st.markdown(f'<div class="product-header">{sp}</div>', unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([1, 1, 1])
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
                
                inputs[sp] = {"fc": f, "tk": (t * qc) + l}
            
            st.markdown("<br>", unsafe_allow_html=True)
            img = st.text_input("🔗 Link hình ảnh")
            note = st.text_area("💬 Ghi chú")

            if st.form_submit_button("🚀 GỬI BÁO CÁO", disabled=(is_blocked or wait_s > 0)):
                p = df_f1[df_f1['SIEU THI'] == sel_st]['PHUONG'].values[0]
                if ht_up == "CTY":
                    rows = [{"NGAY": today_str, "GIO": now.strftime("%H:%M:%S"), "NHAN VIEN": sel_nv, "HE THONG": sel_ht, "PHUONG": p, "SIEU THI": sel_st, "SAN PHAM": "Check-in CTY", "FACING": 0, "TON KHO": 0, "GHI CHU": note, "HINH ANH": img}]
                else:
                    rows = [{"NGAY": today_str, "GIO": now.strftime("%H:%M:%S"), "NHAN VIEN": sel_nv, "HE THONG": sel_ht, "PHUONG": p, "SIEU THI": sel_st, "SAN PHAM": s, "FACING": v['fc'], "TON KHO": v['tk'], "GHI CHU": note, "HINH ANH": img} for s, v in inputs.items() if v['fc'] > 0 or v['tk'] > 0]
                
                if rows and safe_append_to_sheets(rows):
                    st.success("✅ Đã gửi!"); st.rerun()

        # --- TIẾN ĐỘ ---
        try:
            df_ut = df_master[(df_master['NHAN VIEN'] == sel_nv) & (df_master['HE THONG'].isin(UU_TIEN_LIST))]
            all_ut = df_ut['SIEU THI'].unique()
            done_ut = df_history[(df_history['NGAY_DT'].dt.month == now.month) & (df_history['NHAN VIEN'] == sel_nv) & (df_history['HE THONG'].isin(UU_TIEN_LIST))]['SIEU THI'].unique()
            debt = [s for s in all_ut if s not in done_ut]
            st.divider()
            st.subheader(f"📊 Mục tiêu tháng {now.month}")
            st.progress(len(done_ut)/len(all_ut) if len(all_ut) > 0 else 0)
            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng UT", len(all_ut)); c2.metric("Đã đi", len(done_ut)); c3.metric("Nợ", len(debt))
            if debt:
                with st.expander("📍 Điểm chưa đi"):
                    for i, d in enumerate(debt, 1): st.write(f"{i}. {d}")
        except: pass
