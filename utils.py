import pandas as pd
import numpy as np
import io
from datetime import datetime, time, timedelta
from typing import List, Union, BinaryIO
#import xlsxwriter

def load_data(file) -> pd.DataFrame:
    """
    Memuat data dari file CSV atau Excel
    
    Args:
        file: File yang diupload (CSV/Excel)
        
    Returns:
        pd.DataFrame: Data yang telah dimuat
        
    Raises:
        ValueError: Jika format file tidak didukung atau data tidak valid
    """
    try:
        # Deteksi tipe file
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            raise ValueError("Format file tidak didukung. Gunakan CSV atau Excel.")
        
        # Validasi kolom yang diperlukan
        required_columns = ['waktu', 'suhu']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Kolom yang diperlukan tidak ditemukan: {missing_columns}")
        
        # Validasi data tidak kosong
        if df.empty:
            raise ValueError("File kosong atau tidak mengandung data.")
        
        return df
    
    except Exception as e:
        raise ValueError(f"Error dalam memuat file: {str(e)}")

def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mempersiapkan data untuk interpolasi
    
    Args:
        df (pd.DataFrame): Data mentah dengan kolom 'waktu' dan 'suhu'
        
    Returns:
        pd.DataFrame: Data yang telah diproses
        
    Raises:
        ValueError: Jika data tidak valid atau tidak dapat diproses
    """
    try:
        # Copy data untuk menghindari perubahan pada data asli
        processed_df = df.copy()
        
        # Hapus baris dengan nilai yang hilang
        processed_df = processed_df.dropna(subset=['waktu', 'suhu'])
        
        if processed_df.empty:
            raise ValueError("Tidak ada data valid setelah membersihkan nilai yang hilang.")
        
        # Konversi kolom waktu ke format string jika perlu
        processed_df['waktu'] = processed_df['waktu'].astype(str)
        
        # Validasi dan konversi format waktu
        processed_df['waktu_decimal'] = processed_df['waktu'].apply(parse_time_to_decimal)
        
        # Validasi nilai suhu
        processed_df['suhu'] = pd.to_numeric(processed_df['suhu'], errors='coerce')
        processed_df = processed_df.dropna(subset=['suhu'])
        
        if processed_df.empty:
            raise ValueError("Tidak ada data suhu yang valid.")
        
        # Validasi rentang suhu yang masuk akal
        temp_min, temp_max = processed_df['suhu'].min(), processed_df['suhu'].max()
        if temp_min < -50 or temp_max > 60:
            raise ValueError(f"Rentang suhu tidak masuk akal: {temp_min:.1f}°C - {temp_max:.1f}°C")
        
        # Urutkan berdasarkan waktu
        processed_df = processed_df.sort_values('waktu_decimal').reset_index(drop=True)
        
        # Hapus duplikat waktu (ambil rata-rata jika ada duplikat)
        processed_df = processed_df.groupby('waktu_decimal').agg({
            'waktu': 'first',
            'suhu': 'mean'
        }).reset_index()
        
        return processed_df
    
    except Exception as e:
        raise ValueError(f"Error dalam memproses data: {str(e)}")

def parse_time_to_decimal(time_str: str) -> float:
    """
    Mengkonversi string waktu ke format decimal
    
    Args:
        time_str (str): String waktu dalam berbagai format
        
    Returns:
        float: Waktu dalam format decimal (jam.menit)
        
    Raises:
        ValueError: Jika format waktu tidak valid
    """
    try:
        # Bersihkan string
        time_str = str(time_str).strip()
        
        # Coba berbagai format waktu
        formats = [
            '%H:%M',      # HH:MM
            '%H.%M',      # HH.MM
            '%H:%M:%S',   # HH:MM:SS
            '%I:%M %p',   # HH:MM AM/PM
            '%H',         # HH saja
        ]
        
        for fmt in formats:
            try:
                if fmt == '%H':
                    # Untuk format jam saja
                    hour = int(float(time_str))
                    return float(hour)
                else:
                    time_obj = datetime.strptime(time_str, fmt).time()
                    return time_obj.hour + time_obj.minute / 60.0
            except ValueError:
                continue
        
        # Jika tidak ada format yang cocok, coba parsing manual
        if ':' in time_str:
            parts = time_str.split(':')
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return hour + minute / 60.0
        
        # Coba sebagai angka decimal langsung
        decimal_time = float(time_str)
        if 0 <= decimal_time <= 24:
            return decimal_time
        
        raise ValueError(f"Format waktu tidak dikenali: {time_str}")
    
    except Exception as e:
        raise ValueError(f"Error parsing waktu '{time_str}': {str(e)}")

def decimal_to_time_str(decimal_time: float) -> str:
    """
    Mengkonversi waktu decimal ke string format HH:MM
    
    Args:
        decimal_time (float): Waktu dalam format decimal
        
    Returns:
        str: Waktu dalam format HH:MM
    """
    hour = int(decimal_time)
    minute = int((decimal_time - hour) * 60)
    return f"{hour:02d}:{minute:02d}"

def create_time_range(start_time: time, end_time: time, interval_minutes: int) -> List[str]:
    """
    Membuat rentang waktu berdasarkan waktu mulai, akhir, dan interval
    
    Args:
        start_time (time): Waktu mulai
        end_time (time): Waktu akhir
        interval_minutes (int): Interval dalam menit
        
    Returns:
        List[str]: List waktu dalam format HH:MM
    """
    times = []
    current_time = datetime.combine(datetime.today(), start_time)
    end_datetime = datetime.combine(datetime.today(), end_time)
    
    # Jika end_time lebih kecil dari start_time, anggap melewati hari
    if end_datetime <= current_time:
        end_datetime += timedelta(days=1)
    
    while current_time <= end_datetime:
        times.append(current_time.strftime("%H:%M"))
        current_time += timedelta(minutes=interval_minutes)
    
    return times

def export_to_excel(combined_data: pd.DataFrame, original_data: pd.DataFrame, 
                   estimated_data: pd.DataFrame) -> bytes:
    """
    Mengekspor hasil ke file Excel dengan multiple sheets
    
    Args:
        combined_data (pd.DataFrame): Data gabungan
        original_data (pd.DataFrame): Data asli
        estimated_data (pd.DataFrame): Data estimasi
        
    Returns:
        bytes: Buffer file Excel
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Sheet 1: Data Gabungan
        combined_data.to_excel(writer, sheet_name='Data Gabungan', index=False)
        
        # Sheet 2: Data Asli
        original_data.to_excel(writer, sheet_name='Data Asli', index=False)
        
        # Sheet 3: Hasil Estimasi
        estimated_data.to_excel(writer, sheet_name='Hasil Estimasi', index=False)
        
        # Sheet 4: Ringkasan Statistik
        stats_data = {
            'Metrik': ['Jumlah Data Asli', 'Jumlah Estimasi', 'Suhu Min (Asli)', 
                      'Suhu Max (Asli)', 'Suhu Min (Estimasi)', 'Suhu Max (Estimasi)',
                      'Rata-rata (Asli)', 'Rata-rata (Estimasi)'],
            'Nilai': [
                len(original_data),
                len(estimated_data),
                f"{original_data['suhu'].mean():.2f}°C",
                f"{estimated_data['suhu_estimasi'].mean():.2f}°C"
            ]
        }
        
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name='Statistik', index=False)
        
        # Formatting untuk membuat file lebih menarik
        workbook = writer.book
        
        # Format header
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        
        # Format data
        data_format = workbook.add_format({
            'border': 1,
            'align': 'center'
        })
        
        # Format angka
        number_format = workbook.add_format({
            'num_format': '0.00',
            'border': 1,
            'align': 'center'
        })
        
        # Terapkan formatting ke setiap sheet
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            
            # Auto adjust column width
            for i, col in enumerate(worksheet.table.columns):
                max_length = max(len(str(col.name)), 15)
                worksheet.set_column(i, i, max_length)
            
            # Format header row
            for col_num in range(len(worksheet.table.columns)):
                worksheet.write(0, col_num, worksheet.table.columns[col_num].name, header_format)
    
    output.seek(0)
    return output.getvalue()

def validate_temperature_data(df: pd.DataFrame) -> dict:
    """
    Memvalidasi data suhu dan memberikan rekomendasi
    
    Args:
        df (pd.DataFrame): Data suhu yang akan divalidasi
        
    Returns:
        dict: Hasil validasi dan rekomendasi
    """
    validation_result = {
        'is_valid': True,
        'warnings': [],
        'errors': [],
        'recommendations': []
    }
    
    try:
        # Validasi jumlah data
        if len(df) < 3:
            validation_result['warnings'].append(
                f"Jumlah data ({len(df)}) sangat sedikit. Minimal 3 titik data untuk interpolasi yang baik."
            )
        elif len(df) < 5:
            validation_result['warnings'].append(
                f"Jumlah data ({len(df)}) terbatas. Disarankan minimal 5 titik data."
            )
        
        # Validasi interval waktu
        if len(df) > 1:
            time_diffs = np.diff(df['waktu_decimal'].values)
            avg_interval = np.mean(time_diffs)
            interval_std = np.std(time_diffs)
            
            if interval_std > 0.5:  # Standar deviasi > 30 menit
                validation_result['warnings'].append(
                    "Interval waktu antar data tidak konsisten. Interpolasi mungkin kurang akurat."
                )
            
            if avg_interval > 6:  # Interval > 6 jam
                validation_result['warnings'].append(
                    f"Interval rata-rata ({avg_interval:.1f} jam) terlalu besar. Disarankan interval < 4 jam."
                )
        
        # Validasi rentang suhu
        temp_range = df['suhu'].max() - df['suhu'].min()
        if temp_range > 30:
            validation_result['warnings'].append(
                f"Rentang suhu ({temp_range:.1f}°C) sangat besar. Pastikan data akurat."
            )
        
        # Deteksi outlier suhu
        q1 = df['suhu'].quantile(0.25)
        q3 = df['suhu'].quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = df[(df['suhu'] < lower_bound) | (df['suhu'] > upper_bound)]
        if len(outliers) > 0:
            validation_result['warnings'].append(
                f"Ditemukan {len(outliers)} data outlier yang mungkin mempengaruhi akurasi."
            )
        
        # Validasi tren yang tidak wajar
        if len(df) > 2:
            # Cek fluktuasi yang ekstrem
            temp_diff = np.diff(df['suhu'].values)
            extreme_changes = np.abs(temp_diff) > 10  # Perubahan > 10°C
            
            if np.any(extreme_changes):
                validation_result['warnings'].append(
                    "Ditemukan perubahan suhu yang ekstrem (>10°C) antar titik data."
                )
        
        # Rekomendasi berdasarkan analisis
        if len(df) >= 5 and interval_std <= 0.5:
            validation_result['recommendations'].append(
                "Data berkualitas baik untuk interpolasi Newton-Gregory."
            )
        
        if temp_range <= 15 and len(outliers) == 0:
            validation_result['recommendations'].append(
                "Rentang suhu wajar dan tidak ada outlier. Hasil estimasi akan lebih akurat."
            )
        
    except Exception as e:
        validation_result['errors'].append(f"Error dalam validasi: {str(e)}")
        validation_result['is_valid'] = False
    
    return validation_result

def generate_sample_data(pattern: str = 'daily') -> pd.DataFrame:
    """
    Menghasilkan data contoh untuk testing
    
    Args:
        pattern (str): Pola data ('daily', 'weekly', 'irregular')
        
    Returns:
        pd.DataFrame: Data contoh
    """
    if pattern == 'daily':
        # Pola suhu harian normal
        times = ['06:00', '09:00', '12:00', '15:00', '18:00', '21:00']
        temps = [20.5, 24.2, 29.8, 32.1, 27.6, 22.3]
        
    elif pattern == 'weekly':
        # Pola suhu mingguan
        times = ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00']
        temps = [18.2, 16.8, 22.4, 28.7, 30.2, 24.1]
        
    elif pattern == 'irregular':
        # Pola tidak teratur
        times = ['07:30', '11:15', '14:45', '17:20', '20:10']
        temps = [21.3, 26.8, 31.5, 29.2, 25.7]
        
    else:
        # Default daily pattern
        times = ['06:00', '12:00', '18:00']
        temps = [22.0, 30.0, 26.0]
    
    return pd.DataFrame({
        'waktu': times,
        'suhu': temps
    })

def format_time_display(time_str: str) -> str:
    """
    Memformat tampilan waktu untuk UI
    
    Args:
        time_str (str): String waktu
        
    Returns:
        str: Waktu yang diformat
    """
    try:
        hour, minute = map(int, time_str.split(':'))
        if hour == 0:
            return f"12:{minute:02d} AM"
        elif hour < 12:
            return f"{hour}:{minute:02d} AM"
        elif hour == 12:
            return f"12:{minute:02d} PM"
        else:
            return f"{hour-12}:{minute:02d} PM"
    except:
        return time_str

def calculate_accuracy_metrics(original_data: pd.DataFrame, estimated_data: pd.DataFrame) -> dict:
    """
    Menghitung metrik akurasi jika ada data pembanding
    (untuk kasus dimana kita memiliki data aktual untuk waktu yang diestimasi)
    
    Args:
        original_data (pd.DataFrame): Data asli
        estimated_data (pd.DataFrame): Data estimasi
        
    Returns:
        dict: Metrik akurasi
    """
    # Fungsi ini akan berguna jika ada data pembanding
    # Untuk implementasi dasar, return kosong
    return {
        'mae': None,  # Mean Absolute Error
        'rmse': None,  # Root Mean Square Error
        'mape': None,  # Mean Absolute Percentage Error
        'note': 'Metrik akurasi memerlukan data pembanding'
    }

def get_temperature_insights(df: pd.DataFrame) -> dict:
    """
    Memberikan insight tentang pola suhu
    
    Args:
        df (pd.DataFrame): Data suhu
        
    Returns:
        dict: Insight tentang pola suhu
    """
    insights = {
        'peak_temperature': df.loc[df['suhu'].idxmax()],
        'lowest_temperature': df.loc[df['suhu'].idxmin()],
        'temperature_trend': 'stable',
        'daily_pattern': 'unknown',
        'recommendations': []
    }
    
    try:
        # Analisis tren
        if len(df) > 2:
            first_half = df.iloc[:len(df)//2]['suhu'].mean()
            second_half = df.iloc[len(df)//2:]['suhu'].mean()
            
            if second_half > first_half + 2:
                insights['temperature_trend'] = 'increasing'
            elif second_half < first_half - 2:
                insights['temperature_trend'] = 'decreasing'
        
        # Deteksi pola harian
        if len(df) >= 3:
            morning_data = df[df['waktu_decimal'] < 12]
            afternoon_data = df[df['waktu_decimal'] >= 12]
            
            if len(morning_data) > 0 and len(afternoon_data) > 0:
                morning_avg = morning_data['suhu'].mean()
                afternoon_avg = afternoon_data['suhu'].mean()
                
                if afternoon_avg > morning_avg + 3:
                    insights['daily_pattern'] = 'typical_daily_cycle'
                elif abs(afternoon_avg - morning_avg) < 2:
                    insights['daily_pattern'] = 'stable_throughout_day'
        
        # Rekomendasi
        temp_range = df['suhu'].max() - df['suhu'].min()
        if temp_range > 15:
            insights['recommendations'].append(
                "Rentang suhu besar - pertimbangkan faktor cuaca eksternal"
            )
        
        if insights['temperature_trend'] == 'increasing':
            insights['recommendations'].append(
                "Tren suhu meningkat - mungkin menuju siang hari"
            )
        
    except Exception as e:
        insights['error'] = f"Error dalam analisis: {str(e)}"
    
    