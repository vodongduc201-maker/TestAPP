import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Test App - Bộ Đếm Ưu Tiên", layout="centered")
st.title("🧪 Test App: Quản Lý Tuyến Ưu Tiên")

# --- 2. THIẾT LẬP KẾT NỐI & THỜI GIAN ---
tz = pytz.timezone('Asia/Ho_Chi_Minh')
now = datetime.now(tz)
conn = st.connection("gsheets", type=GSheetsConnection)

# Danh sách 8 hệ thống cần viếng thăm (Ưu tiên)
UU_TIEN_LIST = ['CM', 'SF', 'CF', 'MM', 'GO!', 'FL', 'SM', 'XTRA']

# --- 3. ĐỌC DỮ LIỆU MASTER (TỪ GITHUB) ---
@st.cache_data(ttl=60)
def load_master():
    try:
        # Đọc file Excel từ GitHub (giống App chính của bạn)
        df = pd.read_excel("data nhan vien.xlsx", header=None)
        df = df.iloc[:, :5]
        df.columns = ['NHAN VIEN', 'HE THONG', 'PHUONG', 'SIEU THI', 'MSKH']
        return df
    except Exception as e:
        st.error(f"❌ Không tìm thấy file 'data nhan vien.xlsx' trên GitHub: {e}")
        return None

df_master = load_master()

if df_master is not None:
    # --- 4. CHỌN NHÂN VIÊN ---
    list_nv = sorted(df_master['NHAN VIEN'].dropna().unique().tolist())
    sel_nv = st.selectbox("👤 Chọn nhân viên để test bộ đếm", options=list_nv)

    if sel_nv:
        st.divider()
        
        # --- 5. LOGIC BỘ ĐẾM THÁNG ---
        try:
            # A. Lấy danh sách siêu thị ƯU TIÊN của nhân viên này trong file Master
            df_target = df_master[
                (df_master['NHAN VIEN'] == sel_nv) & 
                (df_master['HE THONG'].isin(UU_TIEN_LIST))
            ]
            list_target = df_target['SIEU THI'].unique().tolist()
            tong_diem_ut = len(list_target)

            # B. Đọc lịch sử viếng thăm từ Google Sheets
            # Lưu ý: Worksheet phải tên là Data_Bao_Cao_MT
            df_history = conn.read(worksheet="Data_Bao_Cao_MT", ttl=0)
            
            if not df_history.empty:
                # Chuyển cột NGAY về định dạng ngày để lọc theo tháng/năm hiện tại
                df_history['NGAY_DT'] = pd.to_datetime(df_history['NGAY'], format='%d/%m/%Y', errors='coerce')
                
                # Lọc điểm đã đi: Đúng tháng, Đúng năm, Đúng nhân viên, Đúng hệ thống ưu tiên
                df_visited_month = df_history[
                    (df_history['NGAY_DT'].dt.month == now.month) & 
                    (df_history['NGAY_DT'].dt.year == now.year) & 
                    (df_history['NHAN VIEN'] == sel_nv) &
                    (df_history['HE THONG'].isin(UU_TIEN_LIST))
                ]
                list_visited = df_visited_month['SIEU THI'].unique().tolist()
            else:
                list_visited = []

            # C. Tính toán con số
            so_da_ghe = len(list_visited)
            con_lai = [s for s in list_target if s not in list_visited]
            so_con_lai = len(con_lai)
            phan_tram = int((so_da_ghe / tong_diem_ut) * 100) if tong_diem_ut > 0 else 0

            # D. Hiển thị Giao diện Bộ đếm
            st.subheader(f"📊 Tiến độ Hệ thống Ưu tiên (Tháng {now.month}/{now.year})")
            
            st.progress(phan_tram / 100)
            st.write(f"Đã phủ được **{phan_tram}%** mục tiêu.")

            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng điểm UT", f"{tong_diem_ut}")
            c2.metric("Đã viếng thăm", f"{so_da_ghe}")
            # Cảnh báo số điểm còn lại
            c3.metric("Chưa viếng", f"{so_con_lai}", delta=f"-{so_con_lai}", delta_color="inverse" if so_con_lai > 0 else "normal")

            if so_con_lai > 0:
                with st.expander("📍 Danh sách chi tiết điểm CHƯA viếng"):
                    for i, st_name in enumerate(con_lai, 1):
                        # Lấy mã hệ thống tương ứng
                        ht_code = df_target[df_target['SIEU THI'] == st_name]['HE THONG'].values[0]
                        st.write(f"{i}. **{ht_code}** - {st_name}")
            else:
                st.balloons()
                st.success("🎉 Xuất sắc! Bạn đã hoàn thành phủ điểm ưu tiên trong tháng!")

        except Exception as e:
            st.warning(f"⚠️ Đang đợi dữ liệu từ Sheets... (Lỗi: {e})")
            st.info("Hãy đảm bảo Tab trong Google Sheets có tên chính xác là: Data_Bao_Cao_MT")

        st.divider()
        st.caption("Ứng dụng đang chạy chế độ Test - Dữ liệu thực tế lấy từ Google Sheets & GitHub")
