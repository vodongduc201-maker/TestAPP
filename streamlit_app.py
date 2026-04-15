import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Báo Cáo MT Chương Dương", page_icon="🥤")

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

# Danh sách hệ thống ưu tiên (Đã có CTY và emart)
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

    if sel_nv == "Chọn nhân viên...":
        st.info("Vui lòng chọn tên để bắt đầu.")
    else:
        try:
            df_history = conn.read(worksheet="Data_Bao_Cao_MT", ttl=0)
            if not df_history.empty:
                df_history['NGAY_DT'] = pd.to_datetime(df_history['NGAY'], format='%d/%m/%Y', errors='coerce')
        except:
            df_history = pd.DataFrame()

        if not df_history.empty:
            df_today = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['NGAY'] == today_str)]
            if not df_today.empty:
                with st.expander(f"✅ Đã báo cáo hôm nay ({today_str})", expanded=False):
                    summary = df_today[['GIO', 'HE THONG', 'SIEU THI']].drop_duplicates(subset=['SIEU THI'])
                    st.table(summary.sort_values(by='GIO', ascending=False))

        st.divider()
        df_f1 = df_master[df_master['NHAN VIEN'] == sel_nv]
        st.subheader("🏢 Thực hiện báo cáo")
        
        c1, c2 = st.columns(2)
        with c1:
            list_ht = sorted(df_f1['HE THONG'].dropna().unique().tolist())
            sel_ht = st.selectbox("2. Hệ thống", options=list_ht)
            df_f2 = df_f1[df_f1['HE THONG'] == sel_ht]
        with c2:
            list_st = sorted(df_f2['SIEU THI'].dropna().unique().tolist())
            sel_st = st.selectbox("3. Siêu thị", options=list_st)

        # Tính toán số lần viếng thăm trong tháng để dùng cho cả cảnh báo và chặn ghi dữ liệu
        so_lan_di = 0
        if not df_history.empty:
            so_lan_di = df_history[
                (df_history['NHAN VIEN'] == sel_nv) & 
                (df_history['SIEU THI'] == sel_st) & 
                (df_history['NGAY_DT'].dt.month == now.month)
            ]['NGAY'].nunique()

        # Nhắc nhở nếu là lần thứ 2
        if sel_ht not in UU_TIEN_LIST and so_lan_di == 2:
            st.warning(f"⚠️ Nhắc nhở: Bạn đã viếng thăm **{sel_st}** 2 lần trong tháng này. Đây là lần cuối cùng hệ thống ghi nhận cho điểm này.")

        ht_up = sel_ht.upper()
        if ht_up in ["SH", "CTY", "BHX"]: list_sp = ["Sa Xi Lon"]
        elif ht_up in ["B'SMART", "GS25"]: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390"]
        elif ht_up in ["EMART", "CS", "CM", "CF", "FL", "XTRA"]: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L"]
        elif ht_up in ["GO!", "GO", "BIGC", "MIO"]: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L", "Soda Kem Lon"]
        else: list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L", "Soda Kem Lon", "Suoi 500mL", "Soda Lon"]

        data_inputs = {}
        with st.form("form_bao_cao", clear_on_submit=True):
            h1, h2, h3 = st.columns([2, 1, 1])
            h1.write("**Sản Phẩm**"); h2.write("**Facing**"); h3.write("**Tồn kho**")
            for sp in list_sp:
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write(f"✅ {sp}")
                f_val = c2.number_input("", min_value=0, step=1, key=f"f_{sp}", label_visibility="collapsed")
                t_val = c3.number_input("", min_value=0, step=1, key=f"t_{sp}", label_visibility="collapsed")
                data_inputs[sp] = {"fc": f_val, "tk": t_val}
            
            hinh_anh = st.text_input("🔗 Link hình ảnh")
            ghi_chu = st.text_area("💬 Ghi chú")

            if st.form_submit_button("🚀 Gửi báo cáo"):
                # --- CHẶN KHÔNG CHO GHI LẦN THỨ 3 ---
                if sel_ht not in UU_TIEN_LIST and so_lan_di >= 2:
                    st.error(f"🚫 KHÔNG THỂ GỬI: Bạn đã viếng thăm '{sel_st}' {so_lan_di} lần. Theo quy định, hệ thống ngoài ưu tiên không ghi nhận quá 2 lần/tháng.")
                else:
                    ten_phuong = df_f2[df_f2['SIEU THI'] == sel_st]['PHUONG'].values[0]
                    rows_to_add = []
                    for sp, v in data_inputs.items():
                        if v['fc'] > 0 or v['tk'] > 0:
                            rows_to_add.append({
                                "NGAY": today_str, "GIO": datetime.now(tz).strftime("%H:%M:%S"),
                                "NHAN VIEN": sel_nv, "HE THONG": sel_ht, "PHUONG": ten_phuong,
                                "SIEU THI": sel_st, "SAN PHAM": sp, "FACING": v['fc'], 
                                "TON KHO": v['tk'], "GHI CHU": ghi_chu, "HINH ANH": hinh_anh
                            })

                    if rows_to_add:
                        if safe_append_to_sheets(rows_to_add):
                            st.success("✅ Đã gửi báo cáo thành công!")
                            st.rerun()
                    else:
                        st.warning("Vui lòng nhập số liệu.")

        # 8. Tiến độ tháng
        st.divider()
        try:
            df_target_all = df_master[(df_master['NHAN VIEN'] == sel_nv) & (df_master['HE THONG'].isin(UU_TIEN_LIST))]
            list_target = df_target_all['SIEU THI'].unique().tolist()
            
            if not df_history.empty:
                df_visited = df_history[
                    (df_history['NGAY_DT'].dt.month == now.month) & 
                    (df_history['NGAY_DT'].dt.year == now.year) &
                    (df_history['NHAN VIEN'] == sel_nv) & 
                    (df_history['HE THONG'].isin(UU_TIEN_LIST))
                ]
                list_visited = df_visited['SIEU THI'].unique().tolist()
            else:
                list_visited = []

            con_lai = [s for s in list_target if s not in list_visited]
            st.subheader(f"📊 Tiến độ tháng {now.month}")
            st.progress(len(list_visited)/len(list_target) if list_target else 0)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Mục tiêu UT", f"{len(list_target)}")
            c2.metric("Đã viếng", f"{len(list_visited)}")
            c3.metric("Còn lại", f"{len(con_lai)}", delta=f"-{len(con_lai)}", delta_color="inverse")

            if con_lai:
                with st.expander(f"📍 Còn {len(con_lai)} điểm ưu tiên chưa đi", expanded=True):
                    for i, name in enumerate(con_lai, 1):
                        info = df_target_all[df_target_all['SIEU THI'] == name].iloc[0]
                        st.write(f"{i}. **{info['HE THONG']}** - {name} (*{info['PHUONG']}*)")
        except:
            st.caption("Tiến độ sẽ hiển thị sau khi có dữ liệu.")
