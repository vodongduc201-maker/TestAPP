import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Báo Cáo MT Chương Dương - Hybrid V2", page_icon="🥤")

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

        # --- NHẮC LỊCH / DI TÍCH LỊCH SỬ ---
        if sel_st != "Chọn siêu thị...":
            history_st = pd.DataFrame()
            if not df_history.empty:
                history_st = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['SIEU THI'] == sel_st)]
            
            if not history_st.empty:
                last_visit = history_st['NGAY_DT'].max()
                if pd.notnull(last_visit):
                    days_ago = (datetime.now(tz).replace(tzinfo=None) - last_visit).days
                    if days_ago == 0:
                        st.info(f"📍 **Hôm nay** bạn đã ghé thăm điểm này rồi.")
                    else:
                        st.warning(f"🕒 Ghé lần cuối: **{last_visit.strftime('%d/%m/%Y')}** (Cách đây **{days_ago} ngày**)")
                else:
                    st.success("✨ Wow, chúc mừng bạn đã khám phá ra 1 di tích lịch sử!")
            else:
                st.success("✨ Wow, chúc mừng bạn đã khám phá ra 1 di tích lịch sử!")

        # --- LOGIC CHẶN ---
        so_lan_di = 0
        if not df_history.empty:
            so_lan_di = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['SIEU THI'] == sel_st) & (df_history['NGAY_DT'].dt.month == now.month)]['NGAY'].nunique()
        
        is_blocked_by_limit = (sel_ht not in UU_TIEN_LIST and so_lan_di >= 2)
        is_blocked_by_date = (now.day > 21 and sel_ht not in UU_TIEN_LIST)
        is_after_work_hours = (sel_ht != 'CTY' and (now.hour * 60 + now.minute) >= (17 * 60 + 10))
        
        can_submit_time = True
        waiting_seconds = 0
        if not df_history.empty:
            user_today = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['NGAY'] == today_str)]
            if not user_today.empty:
                last_time = tz.localize(datetime.strptime(f"{today_str} {user_today.iloc[-1]['GIO']}", "%d/%m/%Y %H:%M:%S"))
                diff = (now - last_time).total_seconds()
                if diff < 120:
                    can_submit_time = False
                    waiting_seconds = int(120 - diff)

        if is_after_work_hours: st.error("🌙 Đã qua 17:10. Hệ thống nghỉ.")
        elif is_blocked_by_date: st.error("🚫 Sau ngày 21 chỉ nhận hàng Ưu tiên.")
        elif is_blocked_by_limit: st.error(f"🚫 Điểm này đã hết lượt tháng này (đã đi {so_lan_di} lần).")
        elif not can_submit_time: st.warning(f"⏳ Vui lòng chờ {waiting_seconds}s.")
        
        submit_ready = (not is_after_work_hours) and (not is_blocked_by_date) and (not is_blocked_by_limit) and can_submit_time

        # --- FORM NHẬP LIỆU (TÁCH LOGIC QUY CÁCH 12 VÀ 24) ---
        ht_up = sel_ht.upper()
        if ht_up in ["SH", "CTY", "BHX"]: list_sp = ["Sa Xi Lon"]
        elif ht_up in ["B'SMART", "GS25"]: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390"]
        elif ht_up in ["EMART", "CS", "CM", "CF", "FL", "XTRA"]: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L"]
        else: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L", "Soda Kem Lon", "Suoi 500mL", "Soda Lon"]

        with st.form("form_bao_cao", clear_on_submit=True):
            st.write("**Nhập số liệu trực tiếp**")
            data_inputs = {}
            for sp in list_sp:
                c_name, c_f, c_t, c_l = st.columns([2.5, 1.2, 1.2, 1.2])
                c_name.write(f"✅ **{sp}**")
                f_val = c_f.number_input("Facing", min_value=0, step=1, key=f"f_{sp}")
                t_val = c_t.number_input("Thùng", min_value=0, step=1, key=f"t_{sp}")
                
                # Logic quy cách theo tên sản phẩm
                quy_cach = 12 if "1.5L" in sp else 24
                le_max = quy_cach - 1
                
                l_val = c_l.number_input(f"Lẻ", min_value=0, max_value=le_max, step=1, key=f"l_{sp}", help=f"Quy cách {quy_cach}")
                
                tong_don_vi = (t_val * quy_cach) + l_val
                data_inputs[sp] = {"fc": f_val, "tk": tong_don_vi}
                if t_val > 0 or l_val > 0:
                    st.caption(f"➡️ Tổng tồn: **{tong_don_vi}** (Quy cách {quy_cach})")

            st.divider()
            hinh_anh = st.text_input("🔗 Link hình ảnh")
            ghi_chu = st.text_area("💬 Ghi chú")

            if st.form_submit_button("🚀 Gửi báo cáo", disabled=not submit_ready):
                ten_phuong = df_f2[df_f2['SIEU THI'] == sel_st]['PHUONG'].values[0]
                rows_to_add = [{
                    "NGAY": today_str, "GIO": now.strftime("%H:%M:%S"),
                    "NHAN VIEN": sel_nv, "HE THONG": sel_ht, "PHUONG": ten_phuong,
                    "SIEU THI": sel_st, "SAN PHAM": sp, "FACING": v['fc'], 
                    "TON KHO": v['tk'], "GHI CHU": ghi_chu, "HINH ANH": hinh_anh
                } for sp, v in data_inputs.items() if v['fc'] > 0 or v['tk'] > 0]
                
                if rows_to_add and safe_append_to_sheets(rows_to_add):
                    st.success("✅ Gửi thành công!")
                    st.rerun()

        # --- TIẾN ĐỘ MỤC TIÊU ---
        st.divider()
        try:
            df_target_all = df_master[(df_master['NHAN VIEN'] == sel_nv) & (df_master['HE THONG'].isin(UU_TIEN_LIST))]
            list_target = df_target_all['SIEU THI'].unique().tolist()
            list_visited = []
            if not df_history.empty:
                list_visited = df_history[(df_history['NGAY_DT'].dt.month == now.month) & (df_history['NHAN VIEN'] == sel_nv) & (df_history['HE THONG'].isin(UU_TIEN_LIST))]['SIEU THI'].unique().tolist()
            
            con_lai = [s for s in list_target if s not in list_visited]
            st.subheader(f"📊 Mục tiêu tháng {now.month}")
            progress_val = len(list_visited)/len(list_target) if list_target else 0
            st.progress(progress_val)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng điểm UT", f"{len(list_target)}")
            c2.metric("Đã viếng", f"{len(list_visited)}")
            c3.metric("Còn nợ", f"{len(con_lai)}", delta_color="inverse")

            if con_lai:
                with st.expander(f"📍 Danh sách {len(con_lai)} điểm cần đi", expanded=True):
                    for i, item in enumerate(con_lai, 1):
                        st.write(f"{i}. {item}")
            else: 
                st.balloons(); st.success("🌟 Hoàn thành 100% mục tiêu.")
        except:
            st.caption("Đang tính toán...")
