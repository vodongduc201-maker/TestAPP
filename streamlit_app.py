import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CẤU HÌNH ---
st.set_page_config(page_title="Báo Cáo MT Chương Dương - v4026", page_icon="🥤")
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
            values = [row.get("NGAY"), row.get("GIO"), row.get("NHAN VIEN"), row.get("HE THONG"), 
                      row.get("PHUONG"), row.get("SIEU THI"), row.get("SAN PHAM"), 
                      row.get("FACING"), row.get("TON KHO"), row.get("GHI CHU"), row.get("HINH ANH")]
            sheet.append_row(values)
        return True
    except Exception as e:
        st.error(f"❌ Lỗi ghi dữ liệu: {e}"); return False

UU_TIEN_LIST = ['CM', 'SF', 'CF', 'MM', 'GO!', 'emart', 'CTY', 'SM', 'XTRA']

@st.cache_data(ttl=90)
def load_master():
    try:
        df = pd.read_excel("data nhan vien.xlsx", header=None).iloc[:, :4]
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

        # --- NHẮC LỊCH / BỘ ĐẾM NGÀY ---
        if sel_st:
            history_st = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['SIEU THI'] == sel_st)] if not df_history.empty else pd.DataFrame()
            if not history_st.empty:
                last_visit = history_st['NGAY_DT'].max()
                if pd.notnull(last_visit):
                    days_ago = (now.replace(tzinfo=None) - last_visit).days
                    if days_ago == 0: st.info("📍 **Hôm nay** bạn đã ghé thăm điểm này rồi.")
                    else: st.warning(f"🕒 Ghé lần cuối: **{last_visit.strftime('%d/%m/%Y')}** (Cách đây **{days_ago} ngày**)")
                else: st.success("✨ Wow, điểm mới hoàn toàn!")
            else: st.success("✨ Wow, điểm mới hoàn toàn!")

            # --- LOGIC CHẶN ---
            so_lan_di = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['SIEU THI'] == sel_st) & (df_history['NGAY_DT'].dt.month == now.month)]['NGAY'].nunique() if not df_history.empty else 0
            is_blocked_by_limit = (sel_ht not in UU_TIEN_LIST and so_lan_di >= 2)
            is_blocked_by_date = (now.day > 21 and sel_ht not in UU_TIEN_LIST)
            is_after_work_hours = (sel_ht != 'CTY' and (now.hour * 60 + now.minute) >= (17 * 60 + 10))
            
            can_submit_time, waiting_seconds = True, 0
            if not df_history.empty:
                user_today = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['NGAY'] == today_str)]
                if not user_today.empty:
                    last_t = tz.localize(datetime.strptime(f"{today_str} {user_today.iloc[-1]['GIO']}", "%d/%m/%Y %H:%M:%S"))
                    diff = (now - last_t).total_seconds()
                    if diff < 120: can_submit_time, waiting_seconds = False, int(120 - diff)

            if is_after_work_hours: st.error("🌙 Đã qua 17:10. Hệ thống nghỉ.")
            elif is_blocked_by_date: st.error("🚫 Sau ngày 21 chỉ nhận hàng Ưu tiên.")
            elif is_blocked_by_limit: st.error(f"🚫 Điểm này đã đi {so_lan_di} lần/tháng.")
            elif not can_submit_time: st.warning(f"⏳ Vui lòng chờ {waiting_seconds}s.")
            
            submit_ready = (not is_after_work_hours) and (not is_blocked_by_date) and (not is_blocked_by_limit) and can_submit_time

            # --- FORM NHẬP LIỆU (v4026 UPDATE) ---
            ht_up = sel_ht.upper()
            if ht_up == "CTY":
                list_sp = []; st.info("🏢 Chế độ check-in Công ty.")
            elif ht_up in ["SH", "BHX"]: list_sp = ["Sa Xi Lon"]
            elif ht_up in ["B'SMART", "GS25"]: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390"]
            elif ht_up in ["EMART", "CS", "CM", "CF", "FL", "XTRA"]: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L"]
            else: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L", "Soda Kem Lon", "Suoi 500mL", "Soda Lon"]

            with st.form("form_v4026", clear_on_submit=True):
                data_inputs = {}
                if list_sp:
                    for sp in list_sp:
                        c_name, c_f, c_t, c_l = st.columns([2.5, 1.2, 1.2, 1.2])
                        c_name.write(f"**{sp}**")
                        f_v = c_f.number_input("F", min_value=0, step=1, key=f"f_{sp}")
                        t_v = c_t.number_input("T", min_value=0, step=1, key=f"t_{sp}")
                        qc = 12 if "1.5L" in sp else 24
                        l_v = c_l.number_input("L", min_value=0, max_value=qc-1, step=1, key=f"l_{sp}")
                        total = (t_v * qc) + l_v
                        data_inputs[sp] = {"fc": f_v, "tk": total}
                        if total > 0: st.caption(f"➡️ Tổng tồn {sp}: **{total}**")
                
                hinh_anh = st.text_input("🔗 Link hình ảnh")
                ghi_chu = st.text_area("💬 Ghi chú")
                if st.form_submit_button("🚀 Gửi báo cáo", disabled=not submit_ready):
                    phuong = df_f1[df_f1['SIEU THI'] == sel_st]['PHUONG'].values[0]
                    if ht_up == "CTY":
                        rows = [{"NGAY": today_str, "GIO": now.strftime("%H:%M:%S"), "NHAN VIEN": sel_nv, "HE THONG": sel_ht, "PHUONG": phuong, "SIEU THI": sel_st, "SAN PHAM": "Check-in CTY", "FACING": 0, "TON KHO": 0, "GHI CHU": ghi_chu, "HINH ANH": hinh_anh}]
                    else:
                        rows = [{"NGAY": today_str, "GIO": now.strftime("%H:%M:%S"), "NHAN VIEN": sel_nv, "HE THONG": sel_ht, "PHUONG": phuong, "SIEU THI": sel_st, "SAN PHAM": k, "FACING": v['fc'], "TON KHO": v['tk'], "GHI CHU": ghi_chu, "HINH ANH": hinh_anh} for k, v in data_inputs.items() if v['fc'] > 0 or v['tk'] > 0]
                    if rows and safe_append_to_sheets(rows):
                        st.success("✅ Thành công!"); st.rerun()
