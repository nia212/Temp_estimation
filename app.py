import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, time
import io
from interpolasi_newton import NewtonGregoryInterpolator
from utils import load_data, prepare_data, create_time_range, export_to_excel

# Konfigurasi halaman
st.set_page_config(
    page_title="Estimasi Suhu dengan Newton-Gregory",
    page_icon="🌡️",
    layout="wide"
)

# Judul aplikasi
st.title("🌡️ Estimasi Suhu dengan Interpolasi Newton-Gregory Maju")
st.markdown("---")

# Sidebar untuk input
st.sidebar.header("⚙️ Pengaturan")

# Upload file
uploaded_file = st.sidebar.file_uploader(
    "Upload Data Suhu (CSV/Excel)",
    type=['csv', 'xlsx', 'xls'],
    help="Format: kolom 'waktu' (HH:MM) dan 'suhu' (°C)"
)

# Contoh data jika tidak ada file yang diupload
if uploaded_file is None:
    st.sidebar.info("💡 Menggunakan data contoh")
    # Data contoh suhu harian
    sample_data = {
        'waktu': ['06:00', '09:00', '12:00', '15:00', '18:00', '21:00'],
        'suhu': [22.5, 25.8, 31.2, 33.7, 28.4, 24.1]
    }
    df = pd.DataFrame(sample_data)
else:
    try:
        df = load_data(uploaded_file)
        st.sidebar.success("✅ Data berhasil dimuat!")
    except Exception as e:
        st.sidebar.error(f"❌ Error: {str(e)}")
        st.stop()

# Validasi data
if df is not None:
    try:
        df_processed = prepare_data(df)
    except Exception as e:
        st.error(f"Error dalam memproses data: {str(e)}")
        st.stop()
    
    # Tampilkan data yang dimuat
    with st.expander("📊 Data Suhu yang Dimuat", expanded=False):
        st.dataframe(df_processed, use_container_width=True)
        st.info(f"Total data: {len(df_processed)} titik suhu")

    # Input rentang waktu untuk estimasi
    st.sidebar.subheader("🎯 Pengaturan Estimasi")
    
    mode = st.sidebar.selectbox(
        "Mode Estimasi",
        ["Waktu Spesifik", "Rentang Jam", "Rentang Hari"]
    )
    
    if mode == "Waktu Spesifik":
        target_time = st.sidebar.time_input(
            "Waktu Target",
            value=time(14, 30),
            help="Pilih waktu untuk estimasi suhu"
        )
        time_targets = [target_time.strftime("%H:%M")]
        
    elif mode == "Rentang Jam":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_time = st.sidebar.time_input("Waktu Mulai", value=time(6, 0))
        with col2:
            end_time = st.sidebar.time_input("Waktu Selesai", value=time(22, 0))
        
        interval = st.sidebar.slider("Interval (menit)", 15, 120, 30)
        time_targets = create_time_range(start_time, end_time, interval)
        
    else:  # Rentang Hari
        days = st.sidebar.slider("Jumlah Hari", 1, 7, 3)
        interval = st.sidebar.slider("Interval (jam)", 1, 6, 2)
        time_targets = []
        for day in range(days):
            for hour in range(0, 24, interval):
                time_targets.append(f"{hour:02d}:00")

    # Opsi tampilan
    show_difference_table = st.sidebar.checkbox("Tampilkan Tabel Selisih Maju", value=False)
    
    # Tombol untuk melakukan estimasi
    if st.sidebar.button("🚀 Estimasi Suhu", type="primary"):
        
        # Membuat interpolator
        interpolator = NewtonGregoryInterpolator(df_processed)
        
        # Melakukan estimasi
        results = []
        for target in time_targets:
            try:
                estimated_temp = interpolator.estimate(target)
                results.append({
                    'waktu': target,
                    'suhu_estimasi': round(estimated_temp, 2)
                })
            except Exception as e:
                st.warning(f"Tidak dapat mengestimasi suhu untuk {target}: {str(e)}")
        
        if results:
            results_df = pd.DataFrame(results)
            
            # Tampilkan hasil
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("📈 Hasil Estimasi")
                st.dataframe(results_df, use_container_width=True)
                
                # Statistik hasil
                st.subheader("📊 Statistik Estimasi")
                temps = results_df['suhu_estimasi']
                col_stats1, col_stats2, col_stats3 = st.columns(3)
                
                with col_stats1:
                    st.metric("Suhu Minimum", f"{temps.min():.1f}°C")
                with col_stats2:
                    st.metric("Suhu Maksimum", f"{temps.max():.1f}°C")
                with col_stats3:
                    st.metric("Suhu Rata-rata", f"{temps.mean():.1f}°C")
            
            with col2:
                st.subheader("🌡️ Grafik Suhu")
                
                # Gabungkan data asli dan estimasi untuk grafik
                fig = go.Figure()
                
                # Data asli
                fig.add_trace(go.Scatter(
                    x=df_processed['waktu_decimal'],
                    y=df_processed['suhu'],
                    mode='markers+lines',
                    name='Data Asli',
                    marker=dict(size=8, color='blue'),
                    line=dict(color='blue', width=2)
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
                    title="Suhu vs Waktu",
                    xaxis_title="Waktu (jam)",
                    yaxis_title="Suhu (°C)",
                    hovermode='x unified',
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Analisis tren
            st.subheader("📝 Analisis Tren Suhu")
            
            # Analisis berdasarkan rentang waktu
            if len(results) > 1:
                temp_diff = results_df['suhu_estimasi'].max() - results_df['suhu_estimasi'].min()
                temp_trend = "naik" if results_df['suhu_estimasi'].iloc[-1] > results_df['suhu_estimasi'].iloc[0] else "turun"
                
                col_analysis1, col_analysis2 = st.columns(2)
                
                with col_analysis1:
                    st.info(f"""
                    **Analisis Periode {mode}:**
                    - Rentang suhu: {temp_diff:.1f}°C
                    - Tren umum: {temp_trend}
                    - Variabilitas: {'Tinggi' if temp_diff > 10 else 'Sedang' if temp_diff > 5 else 'Rendah'}
                    """)
                
                with col_analysis2:
                    # Distribusi suhu
                    fig_hist = px.histogram(
                        results_df, 
                        x='suhu_estimasi',
                        title="Distribusi Suhu Estimasi",
                        nbins=10
                    )
                    fig_hist.update_layout(height=300)
                    st.plotly_chart(fig_hist, use_container_width=True)
            
            # Tabel selisih maju (opsional)
            if show_difference_table:
                st.subheader("🔢 Tabel Selisih Maju Newton-Gregory")
                try:
                    diff_table = interpolator.get_difference_table()
                    st.dataframe(diff_table, use_container_width=True)
                    
                    st.info("💡 Tabel di atas menunjukkan selisih maju yang digunakan dalam interpolasi Newton-Gregory")
                except Exception as e:
                    st.warning(f"Tidak dapat menampilkan tabel selisih: {str(e)}")
            
            # Tombol download
            st.subheader("💾 Unduh Hasil")
            
            # Gabungkan data asli dan estimasi
            combined_data = pd.concat([
                df_processed[['waktu', 'suhu']].rename(columns={'suhu': 'suhu_asli'}),
                results_df[['waktu', 'suhu_estimasi']]
            ], ignore_index=True).fillna('')
            
            excel_buffer = export_to_excel(combined_data, df_processed, results_df)
            
            st.download_button(
                label="📥 Download Hasil (Excel)",
                data=excel_buffer,
                file_name=f"estimasi_suhu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        else:
            st.error("Tidak ada hasil estimasi yang berhasil diperoleh.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>🌡️ <b>Aplikasi Estimasi Suhu dengan Interpolasi Newton-Gregory Maju</b></p>
    <p>Dibuat dengan Python, Streamlit, dan metode numerik klasik</p>
</div>
""", unsafe_allow_html=True)