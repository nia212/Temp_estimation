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

def export_to_excel(results_df, original_df, interpolator=None):
    """Export hasil ke Excel dengan detail perhitungan"""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Format untuk header
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4CAF50',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        # Format untuk data
        data_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })
        
        # Format untuk angka
        number_format = workbook.add_format({
            'num_format': '0.0000',
            'align': 'center',
            'border': 1
        })
        
        # Sheet 1: Hasil Estimasi
        results_df.to_excel(writer, sheet_name='Hasil Estimasi', index=False, startrow=1)
        worksheet1 = writer.sheets['Hasil Estimasi']
        worksheet1.write('A1', 'HASIL ESTIMASI SUHU', header_format)
        
        # Format kolom hasil estimasi
        for col_num, col_name in enumerate(results_df.columns):
            worksheet1.write(1, col_num, col_name, header_format)
            if 'suhu' in col_name.lower():
                worksheet1.set_column(col_num, col_num, 15, number_format)
            else:
                worksheet1.set_column(col_num, col_num, 12, data_format)
        
        # Sheet 2: Data Asli
        original_display = original_df[['waktu', 'suhu']].copy()
        original_display.to_excel(writer, sheet_name='Data Asli', index=False, startrow=1)
        worksheet2 = writer.sheets['Data Asli']
        worksheet2.write('A1', 'DATA SUHU ASLI', header_format)
        
        # Format kolom data asli
        for col_num, col_name in enumerate(original_display.columns):
            worksheet2.write(1, col_num, col_name, header_format)
            if 'suhu' in col_name.lower():
                worksheet2.set_column(col_num, col_num, 12, number_format)
            else:
                worksheet2.set_column(col_num, col_num, 12, data_format)
        
        # Sheet 3: Tabel Selisih Maju (jika ada interpolator)
        if interpolator:
            diff_table = interpolator.get_difference_table()
            diff_table.to_excel(writer, sheet_name='Tabel Selisih Maju', index=True, startrow=1)
            worksheet3 = writer.sheets['Tabel Selisih Maju']
            worksheet3.write('A1', 'TABEL SELISIH MAJU NEWTON-GREGORY', header_format)
            
            # Format tabel selisih
            for col_num in range(len(diff_table.columns) + 1):  # +1 untuk index
                if col_num == 0:
                    worksheet3.set_column(col_num, col_num, 8, data_format)
                elif col_num <= 2:
                    worksheet3.set_column(col_num, col_num, 12, data_format)
                else:
                    worksheet3.set_column(col_num, col_num, 12, number_format)
        
        # Sheet 4: Detail Perhitungan (jika ada)
        if interpolator and hasattr(interpolator, 'calculation_details') and interpolator.calculation_details:
            # Buat DataFrame dari detail perhitungan
            details_data = []
            for detail in interpolator.calculation_details:
                details_data.append({
                    'Langkah': detail['step'],
                    'Keterangan': detail['description'],
                    'Nilai': detail['value']
                })
            
            details_df = pd.DataFrame(details_data)
            details_df.to_excel(writer, sheet_name='Detail Perhitungan', index=False, startrow=1)
            worksheet4 = writer.sheets['Detail Perhitungan']
            worksheet4.write('A1', 'DETAIL PERHITUNGAN INTERPOLASI', header_format)
            
            # Format detail perhitungan
            worksheet4.set_column('A:A', 15, data_format)  # Langkah
            worksheet4.set_column('B:B', 50, data_format)  # Keterangan
            worksheet4.set_column('C:C', 15, number_format)  # Nilai
            
            # Header untuk detail
            for col_num, col_name in enumerate(details_df.columns):
                worksheet4.write(1, col_num, col_name, header_format)
        
        # Sheet 5: Ringkasan Metode
        summary_data = [
            ['Metode', 'Interpolasi Newton-Gregory Maju'],
            ['Jumlah Titik Data', len(original_df)],
            ['Rentang Waktu', f"{original_df['waktu'].min()} - {original_df['waktu'].max()}"],
            ['Rentang Suhu', f"{original_df['suhu'].min():.1f}°C - {original_df['suhu'].max():.1f}°C"],
            ['Jumlah Estimasi', len(results_df)],
        ]
        
        if interpolator:
            summary_data.extend([
                ['Interval Data (h)', f"{interpolator.h:.4f}"],
                ['Derajat Polinomial Max', min(len(original_df)-1, 4)]
            ])
        
        summary_df = pd.DataFrame(summary_data, columns=['Parameter', 'Nilai'])
        summary_df.to_excel(writer, sheet_name='Ringkasan', index=False, startrow=1)
        worksheet5 = writer.sheets['Ringkasan']
        worksheet5.write('A1', 'RINGKASAN ANALISIS', header_format)
        
        # Format ringkasan
        worksheet5.set_column('A:A', 20, data_format)
        worksheet5.set_column('B:B', 25, data_format)
        for col_num, col_name in enumerate(summary_df.columns):
            worksheet5.write(1, col_num, col_name, header_format)
    
    return output.getvalue()

