import pandas as pd
import numpy as np
import io

def load_data(file):
    """Load data dari file CSV/Excel"""
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        # Validasi kolom
        if 'waktu' not in df.columns or 'suhu' not in df.columns:
            raise ValueError("File harus memiliki kolom 'waktu' dan 'suhu'")
        
        return df
    except Exception as e:
        raise ValueError(f"Error loading file: {e}")

def prepare_data(df):
    """Siapkan data untuk interpolasi"""
    # Bersihkan data
    df_clean = df.dropna(subset=['waktu', 'suhu']).copy()
    
    if df_clean.empty:
        raise ValueError("Tidak ada data valid")
    
    # Konversi waktu ke decimal
    df_clean['waktu_decimal'] = df_clean['waktu'].apply(time_to_decimal)
    
    # Konversi suhu ke numeric
    df_clean['suhu'] = pd.to_numeric(df_clean['suhu'], errors='coerce')
    df_clean = df_clean.dropna(subset=['suhu'])
    
    # Validasi suhu
    if df_clean['suhu'].min() < -50 or df_clean['suhu'].max() > 60:
        raise ValueError("Rentang suhu tidak wajar")
    
    # Urutkan berdasarkan waktu
    df_clean = df_clean.sort_values('waktu_decimal').reset_index(drop=True)
    
    return df_clean

def time_to_decimal(time_str):
    """Konversi waktu ke format decimal"""
    try:
        time_str = str(time_str).strip()
        
        # Format HH:MM
        if ':' in time_str:
            parts = time_str.split(':')
            hour = int(parts[0])
            minute = int(parts[1])
            return hour + minute / 60.0
        
        # Format decimal
        return float(time_str)
    
    except:
        raise ValueError(f"Format waktu tidak valid: {time_str}")

def export_to_excel(results_df, original_df):
    """Export hasil ke Excel"""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Sheet hasil estimasi
        results_df.to_excel(writer, sheet_name='Hasil Estimasi', index=False)
        
        # Sheet data asli
        original_df[['waktu', 'suhu']].to_excel(writer, sheet_name='Data Asli', index=False)
    
    return output.getvalue()