import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Báo Cáo MT Chương Dương - Hybrid", page_icon="🥤")

# --- 2. THIẾT LẬP KẾT NỐI & THỜI GIAN ---
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
            values = [
                row.get("NGAY"), row.get("GIO"), row.get("NHAN VIEN"), 
                row.get("HE THONG"), row.get("PHUONG"), row.get("SIEU THI"), 
                row.get("SAN PHAM"), row.get("FACING"), row.get("TON KHO"), 
                row.get("GHI CHU"), row.get("HINH ANH")
            ]
            sheet.append_row(values)
        return True
    except Exception as e:
        st.error(f"❌ Lỗi ghi dữ liệu: {e}")
        return False

# Danh sách hệ thống ưu tiên
UU_TIEN_LIST = ['CM', 'SF', 'CF', 'MM', 'GO!', 'emart', 'CTY', 'SM', 'XTRA']

@st.cache_data(ttl=90)
def load_master():
    try:
        df = pd.read_excel("data nhan vien.xlsx", header=None)
        df = df.iloc[:, :4] 
        df.columns = ['NHAN VIEN', 'HE THONG', 'PHUONG', 'SIEU THI']
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"❌ Lỗi file Master: {e}")
        return None

df_master = load_master()

st.title("🥤 Báo Cáo MT Chương Dương")
st.caption("Phiên bản kết hợp: Nhập Thùng/Lon & Siết giới hạn (21/5)")

if df_master is not None:
    list_nv = ["Chọn nhân viên..."] + sorted(df_master['NHAN VIEN'].unique().tolist())
    sel_nv = st.selectbox("👤 1. Nhân viên", options=list_nv)

    if sel_nv != "Chọn nhân viên...":
        try:
            df_history = conn.read(worksheet="Data_Bao_Cao_MT", ttl=0)
            if not df_history.empty:
                df_history['NGAY_DT'] = pd.to_datetime(df_history['NGAY'], format='%d/%m/%Y', errors='coerce')
        except:
            df_history = pd.DataFrame()

        # Hiển thị tóm tắt hôm nay
        if not df_history.empty:
            df_today = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['NGAY'] == today_str)]
            if not df_today.empty:
                with st.expander(f"✅ Đã báo cáo hôm nay ({today_str})", expanded=False):
                    summary = df_today[['GIO', 'HE THONG', 'SIEU THI']].drop_duplicates(subset=['SIEU THI'])
                    st.table(summary.sort_values(by='GIO', ascending=False))

        st.divider()
        df_f1 = df_master[df_master['NHAN VIEN'] == sel_nv]
        c1, c2 = st.columns(2)
        with c1:
            list_ht = sorted(df_f1['HE THONG'].dropna().unique().tolist())
            sel_ht = st.selectbox("2. Hệ thống", options=list_ht)
            df_f2 = df_f1[df_f1['HE THONG'] == sel_ht]
        with c2:
            list_st = sorted(df_f2['SIEU THI'].dropna().unique().tolist())
            sel_st = st.selectbox("3. Siêu thị", options=list_st)

        # --- LOGIC CHẶN (HYBRID) ---
        # 1. Giới hạn 2 lần/tháng (Cập nhật Tháng 5)
        so_lan_di = 0
        is_blocked_by_limit = False
        if not df_history.empty:
            so_lan_di = df_history[
                (df_history['NHAN VIEN'] == sel_nv) & 
                (df_history['SIEU THI'] == sel_st) & 
                (df_history['NGAY_DT'].dt.month == now.month)
            ]['NGAY'].nunique()
            if sel_ht not in UU_TIEN_LIST and so_lan_di >= 2:
                is_blocked_by_limit = True

        # 2. Chặn sau ngày 21 (Cập nhật Tháng 5)
        is_blocked_by_date = False
        if now.day > 21 and sel_ht not in UU_TIEN_LIST:
            is_blocked_by_date = True

        # 3. Chặn giờ giấc (17:10)
        is_after_work_hours = False
        limit_time_total = 17 * 60 + 10
        if sel_ht != 'CTY' and (now.hour * 60 + now.minute) >= limit_time_total:
            is_after_work_hours = True

        # 4. Giãn cách 2 phút
        can_submit_time = True
        waiting_seconds = 0
        if not df_history.empty:
            user_today = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['NGAY'] == today_str)]
            if not user_today.empty:
                last_report_str = user_today.iloc[-1]['GIO']
                last_time = tz.localize(datetime.strptime(f"{today_str} {last_report_str}", "%d/%m/%Y %H:%M:%S"))
                diff = (now - last_time).total_seconds()
                if diff < 120:
                    can_submit_time = False
                    waiting_seconds = int(120 - diff)

        # Thông báo trạng thái
        if is_after_work_hours: st.error("🌙 Tới giờ nghỉ rồi 17:10. Hệ thống đi ngủ đây.")
        elif is_blocked_by_date: st.error("🚫 Sau ngày 21, hệ thống chỉ nhận báo cáo điểm Ưu tiên.")
        elif is_blocked_by_limit: st.error(f"🚫 Điểm này đã đi {so_lan_di} lần. Hết lượt tháng này.")
        elif not can_submit_time: st.warning(f"⏳ Chờ {waiting_seconds} giây nhé.")
        
        submit_ready = (not is_after_work_hours) and (not is_blocked_by_date) and (not is_blocked_by_limit) and can_submit_time

        # --- PHẦN NHẬP LIỆU (THÙNG & LON) ---
        ht_up = sel_ht.upper()
        # (Danh sách sản phẩm giữ nguyên như cũ...)
        if ht_up in ["SH", "CTY", "BHX"]: list_sp = ["Sa Xi Lon"]
        elif ht_up in ["B'SMART", "GS25"]: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390"]
        elif ht_up in ["EMART", "CS", "CM", "CF", "FL", "XTRA"]: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L"]
        else: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L", "Soda Kem Lon", "Suoi 500mL", "Soda Lon"]

        with st.form("form_bao_cao", clear_on_submit=True):
            st.write("**Nhập số liệu (T = Thùng | L = Lon)**")
            data_inputs = {}
            for sp in list_sp:
                c_name, c_f, c_t, c_l = st.columns([2, 1, 1, 1])
                c_name.write(f"✅ {sp}")
                f_val = c_f.number_input("Facing", min_value=0, step=1, key=f"f_{sp}")
                thung = c_t.number_input("T", min_value=0, step=1, key=f"t_{sp}")
                lon = c_l.number_input("L", min_value=0, max_value=23, step=1, key=f"l_{sp}")
                
                tong_lon = (thung * 24) + lon
                data_inputs[sp] = {"fc": f_val, "tk": tong_lon}
                if thung > 0 or lon > 0:
                    st.caption(f"➡️ {sp}: {thung} thùng, {lon} lon = **{tong_lon} lon**")

            hinh_anh = st.text_input("🔗 Link hình ảnh")
            ghi_chu = st.text_area("💬 Ghi chú")

            if st.form_submit_button("🚀 Gửi báo cáo", disabled=not submit_ready):
                ten_phuong = df_f2[df_f2['SIEU THI'] == sel_st]['PHUONG'].values[0]
                rows_to_add = []
                for sp, v in data_inputs.items():
                    if v['fc'] > 0 or v['tk'] > 0:
                        rows_to_add.append({
                            "NGAY": today_str, "GIO": now.strftime("%H:%M:%S"),
                            "NHAN VIEN": sel_nv, "HE THONG": sel_ht, "PHUONG": ten_phuong,
                            "SIEU THI": sel_st, "SAN PHAM": sp, "FACING": v['fc'], 
                            "TON KHO": v['tk'], "GHI CHU": ghi_chu, "HINH ANH": hinh_anh
                        })
                if rows_to_add and safe_append_to_sheets(rows_to_add):
                    st.success("✅ Gửi thành công!")
                    st.rerun()
