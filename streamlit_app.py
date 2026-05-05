import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Báo Cáo MT Chương Dương - v4026", page_icon="🥤", layout="centered")

# --- 2. CSS BOXED UI (TỐI ƯU CHO MOBILE) ---
st.markdown("""
    <style>
    .stSelectbox, .stNumberInput, .stTextArea, .stTextInput {
        background-color: var(--secondary-bg-color);
        padding: 4px; border-radius: 10px; border: 1px solid rgba(128, 128, 128, 0.1);
    }
    .product-box {
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 12px; border-radius: 15px; margin-bottom: 12px;
        background-color: var(--background-color);
        box-shadow: 0px 2px 8px rgba(0, 0, 0, 0.05);
    }
    .product-header {
        background-color: var(--secondary-bg-color); color: var(--text-color);
        padding: 6px 12px; border-radius: 8px; border-left: 5px solid #ff4b4b;
        font-weight: bold; font-size: 14px; margin-bottom: 10px;
    }
    .stButton button {
        width: 100%; height: 55px; background-color: #ff4b4b !important;
        color: white !important; font-weight: bold; border-radius: 15px;
        box-shadow: 0px 4px 10px rgba(255, 75, 75, 0.3); margin-top: 15px;
    }
    .stCaption { text-align: center; font-size: 11px !important; margin-top: -5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. KẾT NỐI & THỜI GIAN ---
tz = pytz.timezone('Asia/Ho_Chi_Minh')
now = datetime.now(tz)
today_str = now.strftime("%d/%m/%Y")
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_append_to_sheets(rows_data):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["connections"]["gsheets"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Data_Bao_Cao_MT").worksheet("Data_Bao_Cao_MT")
        
        # Chuyển đổi list dict sang list values để append_rows (tối ưu tốc độ)
        rows_to_send = []
        for r in rows_data:
            rows_to_send.append([
                r.get("NGAY"), r.get("GIO"), r.get("NHAN VIEN"), r.get("HE THONG"),
                r.get("PHUONG"), r.get("SIEU THI"), r.get("SAN PHAM"),
                r.get("FACING"), r.get("TON KHO"), r.get("GHI CHU"), r.get("HINH ANH")
            ])
        sheet.append_rows(rows_to_send)
        return True
    except Exception as e:
        st.error(f"❌ Lỗi ghi dữ liệu: {e}")
        return False

# --- 4. TẢI MASTER DATA ---
@st.cache_data(ttl=600)
def load_master():
    try:
        df = pd.read_excel("data nhan vien.xlsx", header=None)
        df = df.iloc[:, :4] 
        df.columns = ['NHAN VIEN', 'HE THONG', 'PHUONG', 'SIEU THI']
        return df.apply(lambda x: x.astype(str).str.strip())
    except: return None

df_master = load_master()
st.title("🥤 Báo Cáo MT")

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
        UU_TIEN_LIST = ['CM', 'SF', 'CF', 'MM', 'GO!', 'EMART', 'CTY', 'SM', 'XTRA']
        user_today = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['NGAY'] == today_str)] if not df_history.empty else pd.DataFrame()

        # --- NHẬT KÝ & NHẮC LỊCH ---
        if not user_today.empty:
            with st.expander("🕒 Nhật ký viếng thăm hôm nay", expanded=False):
                log_visit = user_today[['GIO', 'SIEU THI']].drop_duplicates(subset=['SIEU THI']).sort_values(by='GIO', ascending=False)
                st.dataframe(log_visit, use_container_width=True, hide_index=True)

        if sel_st and ht_up != "CTY":
            history_st = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['SIEU THI'] == sel_st)] if not df_history.empty else pd.DataFrame()
            so_lan_thang_nay = history_st[history_st['NGAY_DT'].dt.month == now.month]['NGAY'].nunique()
            last_visit_dt = history_st['NGAY_DT'].max() if not history_st.empty else None
            
            if pd.notnull(last_visit_dt):
                days_ago = (now.replace(tzinfo=None) - last_visit_dt).days
                if days_ago == 0: st.info(f"📍 Hôm nay đã ghé. (Tháng này: {so_lan_thang_nay} lần)")
                else: st.warning(f"🕒 Ghé lần cuối: {last_visit_dt.strftime('%d/%m/%Y')} ({days_ago} ngày trước)")
                
                if ht_up not in UU_TIEN_LIST and so_lan_thang_nay == 1:
                    st.error("⚠️ NHẮC NHỞ: Điểm này đã đi 1 lần. Đây là lượt cuối trong tháng!")
            else: st.success("✨ Điểm bán mới!")

        # --- LOGIC CHẶN ---
        is_overtime = (ht_up != 'CTY' and (now.hour * 60 + now.minute) >= (17 * 60 + 10))
        is_blocked_date = (now.day > 21 and ht_up not in UU_TIEN_LIST)
        is_blocked_limit = (ht_up not in UU_TIEN_LIST and so_lan_thang_nay >= 2)
        
        wait_time = 0
        if not user_today.empty:
            last_time = datetime.strptime(f"{today_str} {user_today.iloc[-1]['GIO']}", "%d/%m/%Y %H:%M:%S")
            diff = (now.replace(tzinfo=None) - last_time).total_seconds()
            if diff < 120: wait_time = int(120 - diff)

        # Thông báo chặn
        if is_overtime: st.error("🌙 Đã sau 17:10. Hẹn gặp lại vào sáng mai!")
        elif is_blocked_date: st.error("🚫 Sau ngày 21: Hệ thống này đã khóa.")
        elif is_blocked_limit: st.error(f"🚫 Điểm này đã đủ {so_lan_thang_nay} lần viếng thăm.")
        elif wait_time > 0: st.warning(f"⏳ Vui lòng đợi {wait_time} giây...")

        # --- 5. DANH SÁCH SẢN PHẨM (ĐÃ TỐI ƯU CM) ---
        if ht_up == "CTY": list_sp = []
        elif ht_up in ["SH", "BHX"]: list_sp = ["Sa Xi Lon"]
        elif ht_up in ["B'SMART", "GS25"]: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390"]
        elif ht_up in ["EMART", "CS", "CM", "CF", "FL", "XTRA"]: 
            list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L"] # Đúng 4 món
        else: 
            list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L", "Soda Kem Lon", "Suoi 500mL", "Soda Lon"]

        # --- 6. FORM NHẬP LIỆU (BOXED UI) ---
        submit_ready = not (is_overtime or is_blocked_date or is_blocked_limit or wait_time > 0)
        
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

            if st.form_submit_button("🚀 GỬI BÁO CÁO", disabled=not submit_ready):
                p = df_f1[df_f1['SIEU THI'] == sel_st]['PHUONG'].values[0]
                rows = []
                if ht_up == "CTY":
                    rows.append({"NGAY": today_str, "GIO": now.strftime("%H:%M:%S"), "NHAN VIEN": sel_nv, "HE THONG": sel_ht, "PHUONG": p, "SIEU THI": sel_st, "SAN PHAM": "Check-in CTY", "FACING": 0, "TON KHO": 0, "GHI CHU": note, "HINH ANH": img})
                else:
                    rows = [{"NGAY": today_str, "GIO": now.strftime("%H:%M:%S"), "NHAN VIEN": sel_nv, "HE THONG": sel_ht, "PHUONG": p, "SIEU THI": sel_st, "SAN PHAM": s, "FACING": v['fc'], "TON KHO": v['tk'], "GHI CHU": note, "HINH ANH": img} for s, v in inputs.items() if v['fc'] > 0 or v['tk'] > 0]
                
                if rows and safe_append_to_sheets(rows):
                    st.success("✅ Gửi thành công!"); st.rerun()

        # --- 7. TIẾN ĐỘ ---
        try:
            df_ut = df_master[(df_master['NHAN VIEN'] == sel_nv) & (df_master['HE THONG'].isin(UU_TIEN_LIST))]
            all_ut = df_ut['SIEU THI'].unique()
            done_ut = df_history[(df_history['NGAY_DT'].dt.month == now.month) & (df_history['NHAN VIEN'] == sel_nv) & (df_history['HE THONG'].isin(UU_TIEN_LIST))]['SIEU THI'].unique()
            debt = [s for s in all_ut if s not in done_ut]
            st.divider()
            st.subheader(f"📊 Mục tiêu tháng {now.month}")
            st.progress(len(done_ut)/len(all_ut) if len(all_ut) > 0 else 0)
            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng UT", len(all_ut))
            c2.metric("Đã đi", len(done_ut))
            c3.metric("Chưa đi", len(debt))
            if debt:
                with st.expander("📍 Danh sách điểm chưa đi"):
                    for i, d in enumerate(debt, 1): st.write(f"{i}. {d}")
        except: pass
