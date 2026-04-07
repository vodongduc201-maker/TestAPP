# --- THEO DÕI TIẾN ĐỘ HỆ THỐNG ƯU TIÊN TRONG THÁNG ---
st.markdown("---")
try:
    # Danh sách hệ thống ưu tiên bạn đã cung cấp
    uu_tien_list = ['CM', 'SF', 'CF', 'MM', 'GO!', 'FL', 'SM', 'XTRA']
    
    # 1. Lọc toàn bộ danh sách điểm cần viếng thăm của NV này (từ file Excel Master)
    # Chỉ lấy các dòng thuộc hệ thống ưu tiên
    df_muc_tieu = df_f2[
        (df_f2['NHAN VIEN'] == sel_nv) & 
        (df_f2['HE THONG'].isin(uu_tien_list))
    ]
    list_st_muc_tieu = df_muc_tieu['SIEU THI'].unique().tolist()
    tong_diem = len(list_st_muc_tieu)

    # 2. Lọc dữ liệu đã đi trong tháng (từ Google Sheets)
    df_history = conn.read(worksheet="Data_Bao_Cao_MT", ttl=0)
    da_ghe_thang = []
    
    if not df_history.empty:
        # Chuyển cột ngày về định dạng datetime
        df_history['NGAY_DT'] = pd.to_datetime(df_history['NGAY'], format='%d/%m/%Y', errors='coerce')
        
        # Lọc theo tháng hiện tại, đúng nhân viên và đúng hệ thống ưu tiên
        df_visited = df_history[
            (df_history['NGAY_DT'].dt.month == now.month) & 
            (df_history['NGAY_DT'].dt.year == now.year) & 
            (df_history['NHAN VIEN'] == sel_nv) &
            (df_history['HE THONG'].isin(uu_tien_list))
        ]
        da_ghe_thang = df_visited['SIEU THI'].unique().tolist()

    # 3. Tính toán con số
    so_da_ghe = len(da_ghe_thang)
    con_lai_list = [s for s in list_st_muc_tieu if s not in da_ghe_thang]
    so_con_lai = len(con_lai_list)
    phan_tram = int((so_da_ghe / tong_diem) * 100) if tong_diem > 0 else 0

    # 4. Hiển thị giao diện
    st.subheader(f"📊 Chỉ tiêu tháng {now.month}/{now.year}")
    st.progress(phan_tram / 100)
    st.write(f"Đã hoàn thành: **{phan_tram}%** mục tiêu hệ thống ưu tiên.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng điểm", tong_diem)
    c2.metric("Đã viếng thăm", so_da_ghe)
    # Nếu còn điểm chưa đi sẽ hiện màu đỏ cảnh báo
    c3.metric("Chưa đi", so_con_lai, delta=-so_con_lai, delta_color="inverse" if so_con_lai > 0 else "normal")

    if so_con_lai > 0:
        with st.expander("📍 Xem danh sách các điểm ưu tiên chưa viếng"):
            for i, st_name in enumerate(con_lai_list, 1):
                # Lấy tên hệ thống tương ứng để nhân viên dễ tìm
                ht_name = df_muc_tieu[df_muc_tieu['SIEU THI'] == st_name]['HE THONG'].values[0]
                st.write(f"{i}. **{ht_name}** - {st_name}")
    else:
        st.success("🎉 Xuất sắc! Bạn đã phủ kín toàn bộ hệ thống ưu tiên trong tháng!")

except Exception as e:
    st.info("Đang tính toán dữ liệu viếng thăm...")
st.markdown("---")
