import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import time
from interpolasi_newton import NewtonGregoryInterpolator
from utils import load_data, prepare_data, export_to_excel

# Konfigurasi halaman
st.set_page_config(page_title="Estimasi Suhu Newton-Gregory", page_icon="🌡️", layout="wide")

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
    target_time = st.sidebar.time_input("Waktu Target", value=time(14, 30))
    time_targets = [target_time.strftime("%H:%M")]
else:
    start_time = st.sidebar.time_input("Waktu Mulai", value=time(8, 0))
    end_time = st.sidebar.time_input("Waktu Selesai", value=time(20, 0))
    interval = st.sidebar.slider("Interval (menit)", 30, 120, 60)
    
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

# Tombol estimasi
if st.sidebar.button("Estimasi Suhu", type="primary"):
    try:
        # Buat interpolator
        interpolator = NewtonGregoryInterpolator(df_processed)
        
        # Estimasi
        results = []
        for target in time_targets:
            try:
                temp = interpolator.estimate(target)
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
            
            with col2:
                st.subheader("Grafik Suhu")
                
                fig = go.Figure()
                
                # Data asli
                fig.add_trace(go.Scatter(
                    x=df_processed['waktu_decimal'],
                    y=df_processed['suhu'],
                    mode='markers+lines',
                    name='Data Asli',
                    line=dict(color='blue')
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
                    marker=dict(size=8, color='red')
                ))
                
                fig.update_layout(
                    xaxis_title="Waktu (jam)",
                    yaxis_title="Suhu (°C)",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Download
            st.subheader("Download Hasil")
            excel_data = export_to_excel(results_df, df_processed)
            st.download_button(
                "Download Excel",
                data=excel_data,
                file_name="hasil_estimasi.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    except Exception as e:
        st.error(f"Error dalam estimasi: {e}")