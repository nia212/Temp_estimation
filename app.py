import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time
from interpolasi_newton import NewtonGregoryInterpolasi
from utils import load_data, prepare_data, export_to_excel

# Konfigurasi halaman
st.set_page_config(page_title="Estimasi Suhu Newton-Gregory", 
                   page_icon="🌡️", 
                   layout="wide")

# Header
st.title("🌡️ Estimasi Suhu dengan Interpolasi Newton-Gregory")
st.markdown("Aplikasi untuk mengestimasi suhu berdasarkan data historis")

# Sidebar input
st.sidebar.header("Input Data")

# Upload file atau gunakan contoh
uploaded_file = st.sidebar.file_uploader("Upload file CSV/Excel", type=['csv', 'xlsx'])

if uploaded_file is None:
    # Data contoh
    sample_data = pd.DataFrame({
        'waktu': ['06:00', '09:00', '12:00', '15:00', '18:00', '21:00'],
        'suhu': [22.5, 25.8, 31.2, 33.7, 28.4, 24.1]
    })
    df = sample_data
    st.sidebar.info("Menggunakan data contoh")
else:
    df = load_data(uploaded_file)

# Proses data
try:
    df_processed = prepare_data(df)
    st.sidebar.success(f"Data berhasil dimuat: {len(df_processed)} titik")
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# Tampilkan data
with st.expander("Data Suhu"):
    st.dataframe(df_processed[['waktu', 'suhu']], use_container_width=True)

# Input estimasi
st.sidebar.subheader("Pengaturan Estimasi")

mode = st.sidebar.selectbox("Mode", ["Waktu Tunggal", "Rentang Waktu"])

if mode == "Waktu Tunggal":
    # Batasan waktu berdasarkan data yang ada
    min_time = df_processed['waktu_decimal'].min()
    max_time = df_processed['waktu_decimal'].max()
    
    # Konversi ke jam dan menit untuk display
    min_hour = int(min_time)
    min_minute = int((min_time - min_hour) * 60)
    max_hour = int(max_time)
    max_minute = int((max_time - max_hour) * 60)
    
    st.sidebar.info(f"Rentang waktu data: {min_hour:02d}:{min_minute:02d} - {max_hour:02d}:{max_minute:02d}")
    
    target_time = st.sidebar.time_input(
        "Waktu Target", 
        value=time(int((min_time + max_time) / 2), 0),
        help=f"Pilih waktu antara {min_hour:02d}:{min_minute:02d} dan {max_hour:02d}:{max_minute:02d}"
    )
    
    # Validasi waktu target
    target_decimal = target_time.hour + target_time.minute/60
    if target_decimal < min_time or target_decimal > max_time:
        st.sidebar.warning(f"⚠️ Waktu target di luar rentang data! Hasil mungkin tidak akurat.")
    
    time_targets = [target_time.strftime("%H:%M")]
else:
    # Batasan waktu berdasarkan data yang ada
    min_time = df_processed['waktu_decimal'].min()
    max_time = df_processed['waktu_decimal'].max()
    
    min_hour = int(min_time)
    min_minute = int((min_time - min_hour) * 60)
    max_hour = int(max_time)
    max_minute = int((max_time - max_hour) * 60)
    
    st.sidebar.info(f"Rentang waktu data: {min_hour:02d}:{min_minute:02d} - {max_hour:02d}:{max_minute:02d}")
    
    start_time = st.sidebar.time_input(
        "Waktu Mulai", 
        value=time(min_hour, min_minute),
        help=f"Waktu mulai (minimal: {min_hour:02d}:{min_minute:02d})"
    )
    end_time = st.sidebar.time_input(
        "Waktu Selesai", 
        value=time(max_hour, max_minute),
        help=f"Waktu selesai (maksimal: {max_hour:02d}:{max_minute:02d})"
    )
    interval = st.sidebar.slider("Interval (menit)", 15, 120, 60)
    
    # Validasi rentang waktu
    start_decimal = start_time.hour + start_time.minute/60
    end_decimal = end_time.hour + end_time.minute/60
    
    if start_decimal < min_time or end_decimal > max_time:
        st.sidebar.warning("⚠️ Rentang waktu di luar data! Hasil di luar rentang mungkin tidak akurat.")
    
    if start_decimal >= end_decimal:
        st.sidebar.error("❌ Waktu mulai harus lebih kecil dari waktu selesai!")
        time_targets = []
    else:
        # Generate time range
        time_targets = []
        current_hour = start_time.hour
        current_minute = start_time.minute
        
        while current_hour < end_time.hour or (current_hour == end_time.hour and current_minute <= end_time.minute):
            time_targets.append(f"{current_hour:02d}:{current_minute:02d}")
            current_minute += interval
            if current_minute >= 60:
                current_hour += current_minute // 60
                current_minute = current_minute % 60
        
        st.sidebar.success(f"✅ {len(time_targets)} titik waktu akan diestimasi")

# Tombol estimasi
if st.sidebar.button(" Estimasi Suhu", type="primary"):
    try:
        # Buat interpolator
        interpolator = NewtonGregoryInterpolasi(df_processed)
        
        # Tampilkan tabel selisih maju
        st.subheader("Tabel Selisih Maju Newton-Gregory")
        diff_table = interpolator.get_difference_table()
        
        # Format tampilan tabel
        styled_table = diff_table.style.format({
            col: '{:.4f}' for col in diff_table.columns if col not in ['Waktu', 'Suhu']
        }).format({'Suhu': '{:.1f}'})
        
        st.dataframe(styled_table, use_container_width=True)
        
        st.markdown("---")

        # Estimasi
        results = []
        
        for target in time_targets:
            try:
                temp = interpolator.estimate_with_details(target)
                results.append({'waktu': target, 'suhu_estimasi': round(temp, 1)})
            except Exception as e:
                st.warning(f"Gagal estimasi untuk {target}: {e}")
        
        if results:
            results_df = pd.DataFrame(results)
            
            # Layout dua kolom
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("Hasil Estimasi")
                st.dataframe(results_df, use_container_width=True)
                
                # Statistik sederhana
                temps = results_df['suhu_estimasi']
                st.write(f"**Rentang:** {temps.min():.1f}°C - {temps.max():.1f}°C")
                st.write(f"**Rata-rata:** {temps.mean():.1f}°C")
                
                if len(temps) > 1:
                    st.write(f"**Std Deviasi:** {temps.std():.2f}°C")
            
            with col2:
                st.subheader("Grafik Suhu")
                
                fig = go.Figure()
                
                # Data asli
                fig.add_trace(go.Scatter(
                    x=df_processed['waktu_decimal'],
                    y=df_processed['suhu'],
                    mode='markers+lines',
                    name='Data Asli',
                    line=dict(color='blue', width=2),
                    marker=dict(size=8, color='blue')
                ))
                
                # Data estimasi
                results_df['waktu_decimal'] = results_df['waktu'].apply(
                    lambda x: int(x.split(':')[0]) + int(x.split(':')[1])/60
                )
                
                fig.add_trace(go.Scatter(
                    x=results_df['waktu_decimal'],
                    y=results_df['suhu_estimasi'],
                    mode='markers',
                    name='Estimasi',
                    marker=dict(size=10, color='red', symbol='diamond')
                ))
                
                fig.update_layout(
                    xaxis_title="Waktu (jam)",
                    yaxis_title="Suhu (°C)",
                    height=400,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    xaxis=dict(showgrid=True),
                    yaxis=dict(showgrid=True)
                )

                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # Download
            st.subheader("Download Hasil")
            
            col_download1, col_download2 = st.columns(2)
            
            with col_download1:
                # Excel dengan detail lengkap
                excel_data = export_to_excel(results_df, df_processed, interpolator)
                st.download_button(
                    "Download Excel Lengkap",
                    data=excel_data,
                    file_name=f"hasil_estimasi_suhu_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            with col_download2:
                # CSV hasil estimasi
                csv_data = results_df.to_csv(index=False)
                st.download_button(
                    "Download CSV Hasil",
                    data=csv_data,
                    file_name=f"estimasi_suhu_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            # Informasi tentang file yang akan didownload
            st.info("""
            **File Excel berisi:**
            - Sheet 1: Hasil Estimasi
            - Sheet 2: Data Asli
            - Sheet 3: Tabel Selisih Maju
            - Sheet 4: Ringkasan Analisis
            """)
            
    except Exception as e:
        st.error(f"Error saat estimasi: {e}")
        st.stop()

# footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; padding: 2rem; background: rgba(255, 255, 255, 0.1); border-radius: 15px; margin-top: 2rem; color: #D6DCF5; font-family: 'Inter', sans-serif;">
    <p> Temperature Estimation System</p>
    <p>Powered by Newton's Gregory Forward Interpolation Algorithm | Version 3 | Last updated: {datetime.now().strftime('%Y-%m-%d')}</p>
</div>
""", unsafe_allow_html=True)