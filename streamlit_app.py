import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pytz

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(page_title="Phòng Thí Nghiệm MT", layout="centered")
st.title("🧪 Test App: Quản Lý Hệ Thống Ưu Tiên")

# --- 2. KẾT NỐI DỮ LIỆU ---
conn = st.connection("gsheets", type=GSheetsConnection)
tz = pytz.timezone('Asia/Ho_Chi_Minh')
now = datetime.now(tz)

# Danh sách 8 hệ thống ưu tiên của bạn Đức
UU_TIEN_LIST = ['CM', 'SF', 'CF', 'MM', 'GO!', 'FL', 'SM', 'XTRA']

# Đọc file Master (data nhan vien)
try:
    df_master = conn.read(worksheet="Data_Bao_Cao_MT", ttl=0)
except Exception as e:
    st.error("Không tìm thấy worksheet 'data nhan vien'. Vui lòng kiểm tra lại tên sheet!")
    st.stop()

# --- 3. CHỌN NHÂN VIÊN ---
sel_nv = st.selectbox("👤 Chọn nhân viên để kiểm tra tiến độ", df_master['NHAN VIEN'].unique())

if sel_nv:
    # --- 4. TÍNH TOÁN TIẾN ĐỘ THÁNG ---
    st.markdown("---")
    st.subheader(f"📊 Chỉ tiêu Hệ thống Ưu tiên (Tháng {now.month})")
    
    try:
        # Lấy danh sách điểm mục tiêu thuộc 8 hệ thống ưu tiên của NV này
        df_target = df_master[
            (df_master['NHAN VIEN'] == sel_nv) & 
            (df_master['HE THONG'].isin(UU_TIEN_LIST))
        ]
        list_target = df_target['SIEU THI'].unique().tolist()
        tong_diem = len(list_target)

        # Đọc lịch sử báo cáo
        df_history = conn.read(worksheet="Data_Bao_Cao_MT", ttl=0)
        
        if not df_history.empty:
            # Ép kiểu ngày tháng để lọc
            df_history['NGAY_DT'] = pd.to_datetime(df_history['NGAY'], format='%d/%m/%Y', errors='coerce')
            
            # Lọc điểm đã ghé trong tháng hiện tại
            df_visited = df_history[
                (df_history['NGAY_DT'].dt.month == now.month) & 
                (df_history['NGAY_DT'].dt.year == now.year) & 
                (df_history['NHAN VIEN'] == sel_nv) &
                (df_history['HE THONG'].isin(UU_TIEN_LIST))
            ]
            list_visited = df_visited['SIEU THI'].unique().tolist()
        else:
            list_visited = []

        # Tính toán con số
        so_da_ghe = len(list_visited)
        con_lai = [s for s in list_target if s not in list_visited]
        so_con_lai = len(con_lai)
        phan_tram = int((so_da_ghe / tong_diem) * 100) if tong_diem > 0 else 0

        # Hiển thị Thanh tiến độ
        st.progress(phan_tram / 100)
        st.write(f"Đã phủ được **{phan_tram}%** các điểm ưu tiên.")

        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng điểm UT", tong_diem)
        c2.metric("Đã viếng thăm", so_da_ghe)
        c3.metric("Còn lại", so_con_lai, delta=-so_con_lai, delta_color="inverse" if so_con_lai > 0 else "normal")

        # Danh sách chi tiết các điểm chưa đi
        if so_con_lai > 0:
            with st.expander("📍 Danh sách điểm ƯU TIÊN chưa viếng"):
                for i, st_name in enumerate(con_lai, 1):
                    # Lấy tên hệ thống để hiển thị kèm theo
                    ht_name = df_target[df_target['SIEU THI'] == st_name]['HE THONG'].values[0]
                    st.write(f"{i}. **{ht_name}** - {st_name}")
        else:
            st.balloons()
            st.success("🎉 Tuyệt vời! Bạn đã hoàn thành 100% mục tiêu ưu tiên!")

    except Exception as e:
        st.info("Đang cập nhật dữ liệu tiến độ...")
    
    st.markdown("---")

    # --- 5. GIAO DIỆN NHẬP LIỆU (TÓM GỌN) ---
    st.info("Nhập báo cáo mới bên dưới 👇")
    # ... (Phần code chọn Siêu thị và gửi báo cáo của bạn tiếp tục ở đây)
