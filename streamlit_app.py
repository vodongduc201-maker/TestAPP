import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Test App - Chương Dương", page_icon="🥤")

# --- 2. THIẾT LẬP KẾT NỐI & THỜI GIAN ---
tz = pytz.timezone('Asia/Ho_Chi_Minh')
now = datetime.now(tz)
today_str = now.strftime("%d/%m/%Y")
conn = st.connection("gsheets", type=GSheetsConnection)

# Danh sách 8 hệ thống ưu tiên
UU_TIEN_LIST = ['CM', 'SF', 'CF', 'MM', 'GO!', 'SM', 'emart']

# --- 3. ĐỌC DANH MỤC TỪ GITHUB (4 CỘT) ---
@st.cache_data(ttl=60)
def load_master():
    try:
        df = pd.read_excel("data nhan vien.xlsx", header=None)
        df = df.iloc[:, :4] 
        df.columns = ['NHAN VIEN', 'HE THONG', 'PHUONG', 'SIEU THI']
        return df
    except Exception as e:
        st.error(f"❌ Lỗi file Master: {e}")
        return None

df_master = load_master()

# --- GIAO DIỆN CHÍNH ---
st.title("🥤 Test App: Báo Cáo Thị Trường")

if df_master is not None:
    # --- CHỌN NHÂN VIÊN ---
    list_nv = ["Chọn nhân viên..."] + sorted(df_master['NHAN VIEN'].dropna().unique().tolist())
    sel_nv = st.selectbox("👤 1. Nhân viên", options=list_nv)

    if sel_nv == "Chọn nhân viên...":
        st.info("Vui lòng chọn tên để bắt đầu.")
    else:
        # Đọc lịch sử từ Sheets
        try:
            df_history = conn.read(worksheet="Data_Bao_Cao_MT", ttl=0)
            if not df_history.empty:
                df_history['NGAY_DT'] = pd.to_datetime(df_history['NGAY'], format='%d/%m/%Y', errors='coerce')
        except:
            df_history = pd.DataFrame()

        # --- 4. HIỂN THỊ CÁC ĐIỂM ĐÃ VIẾNG THĂM HÔM NAY ---
        if not df_history.empty:
            df_today = df_history[(df_history['NHAN VIEN'] == sel_nv) & (df_history['NGAY'] == today_str)]
            if not df_today.empty:
                with st.expander(f"✅ Đã báo cáo hôm nay ({today_str})", expanded=False):
                    summary_points = df_today[['GIO', 'HE THONG', 'SIEU THI']].drop_duplicates(subset=['SIEU THI'])
                    summary_points = summary_points.sort_values(by='GIO', ascending=False)
                    st.table(summary_points)
            else:
                st.caption("✨ Bạn chưa có báo cáo nào trong ngày hôm nay.")

        # --- 5. CHỌN TUYẾN ĐI & FORM NHẬP BÁO CÁO ---
        st.divider()
        df_f1 = df_master[df_master['NHAN VIEN'] == sel_nv]
        st.subheader("🏢 Thực hiện báo cáo")
        
        col_ht, col_st = st.columns(2)
        with col_ht:
            list_ht = sorted(df_f1['HE THONG'].dropna().unique().tolist())
            sel_ht = st.selectbox("2. Hệ thống", options=list_ht)
            df_f2 = df_f1[df_f1['HE THONG'] == sel_ht]
        with col_st:
            list_st = sorted(df_f2['SIEU THI'].dropna().unique())
            sel_st = st.selectbox("3. Siêu thị", options=list_st)

        # Cảnh báo nếu ngoài ưu tiên mà đã đi rồi
        if sel_ht not in UU_TIEN_LIST and not df_history.empty:
            da_di_thang = df_history[(df_history['NGAY_DT'].dt.month == now.month) & (df_history['SIEU THI'] == sel_st)]
            if not da_di_thang.empty:
                st.warning(f"⚠️ Điểm này đi {len(da_di_thang['NGAY'].unique())} lần trong tháng rồi. Đi mấy điểm lấy đơn hàng đi mấy ông bà nội!")

        # Logic sản phẩm theo nhóm hệ thống
        ht_check = sel_ht.upper().strip()
        if ht_check in ["SH", "BHX"]: 
            list_sp = ["Sa Xi Lon"]
        elif ht_check in ["B'SMART", "GS25"]: 
            list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390"]
        elif ht_check in ["EMART", "CS", "CM", "CF", "FL", "XTRA"]: 
            list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L"]
        elif ht_check in ["GO!", "GO", "BIGC", "MIO"]: 
            list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L", "Soda Kem Lon"]
        else: 
            list_sp = ["Sa Xi Lon", "Sa Xi Zero Lon", "Xi Pet 390", "Xi Pet 1.5L", "Soda Kem Lon", "Suoi 500mL", "Soda Lon"]
        
        data_inputs = {}
        with st.form("form_bao_cao", clear_on_submit=True):
            h1, h2, h3 = st.columns([2, 1, 1])
            h1.write("**Sản Phẩm**"); h2.write("**Facing**"); h3.write("**Tồn kho**")
            for sp in list_sp:
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write(f"✅ {sp}")
                f_val = c2.number_input("", min_value=0, step=1, key=f"fc_{sp}", label_visibility="collapsed")
                t_val = c3.number_input("", min_value=0, step=1, key=f"tk_{sp}", label_visibility="collapsed")
                data_inputs[sp] = {"fc": f_val, "tk": t_val}
            
            hinh_anh = st.text_input("🔗 Link hình ảnh")
            ghi_chu = st.text_area("💬 Ghi chú")

            if st.form_submit_button("🚀 Gửi báo cáo"):
                ten_phuong = df_f2[df_f2['SIEU THI'] == sel_st]['PHUONG'].values[0]
                rows_to_add = []
                for sp, values in data_inputs.items():
                    if values['fc'] > 0 or values['tk'] > 0:
                        rows_to_add.append({
                            "NGAY": today_str, "GIO": datetime.now(tz).strftime("%H:%M:%S"),
                            "NHAN VIEN": sel_nv, "HE THONG": sel_ht, "PHUONG": ten_phuong,
                            "SIEU THI": sel_st, "SAN PHAM": sp, 
                            "FACING": values['fc'], "TON KHO": values['tk'],
                            "GHI CHU": ghi_chu, "HINH ANH": hinh_anh
                        })

                if rows_to_add:
                    df_new = pd.DataFrame(rows_to_add)
                    # Gộp vào lịch sử cũ và cập nhật
                    df_final = pd.concat([df_new, df_history], ignore_index=True)
                    # Loại bỏ cột phụ NGAY_DT trước khi lưu
                    if 'NGAY_DT' in df_final.columns: df_final = df_final.drop(columns=['NGAY_DT'])
                    conn.update(worksheet="Data_Bao_Cao_MT", data=df_final)
                    st.success(f"✅ Đã gửi báo cáo thành công cho {sel_st}!")
                    st.rerun()
                else:
                    st.warning("Vui lòng nhập ít nhất một số liệu.")

        # --- 6. BỘ ĐẾM TIẾN ĐỘ THÁNG (DỜI XUỐNG DƯỚI CÙNG) ---
        st.divider()
        try:
            # Lấy mục tiêu ưu tiên
            df_target = df_master[(df_master['NHAN VIEN'] == sel_nv) & (df_master['HE THONG'].isin(UU_TIEN_LIST))]
            list_target = df_target['SIEU THI'].unique().tolist()
            tong_diem_ut = len(list_target)

            # Lấy các điểm đã đi trong hệ thống ưu tiên tháng này
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

            so_con_lai = len([s for s in list_target if s not in list_visited])
            phan_tram = int((len(list_visited) / tong_diem_ut) * 100) if tong_diem_ut > 0 else 0

            st.subheader(f"📊 Tổng kết tiến độ tháng {now.month}")
            st.progress(phan_tram / 100)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Mục tiêu ưu tiên", f"{tong_diem_ut} CH")
            c2.metric("Đã hoàn thành", f"{len(list_visited)} CH")
            c3.metric("Còn lại", f"{so_con_lai} CH", delta=f"-{so_con_lai}", delta_color="inverse")

            if so_con_lai > 0:
                with st.expander("📍 Xem danh sách các điểm ưu tiên chưa ghé"):
                    con_lai_names = [s for s in list_target if s not in list_visited]
                    for i, name in enumerate(con_lai_names, 1):
                        ht_type = df_target[df_target['SIEU THI'] == name]['HE THONG'].values[0]
                        st.write(f"{i}. **{ht_type}** - {name}")
            else:
                st.success("🎉 Chúc mừng! Bạn đã phủ xong 100% các điểm ưu tiên tháng này!")
        except Exception as e:
            st.caption("Tiến độ sẽ cập nhật sau khi bạn gửi báo cáo.")
