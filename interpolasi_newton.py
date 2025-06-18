import numpy as np
import pandas as pd
from typing import List, Tuple, Optional

class NewtonGregoryInterpolator:
    """
    Kelas untuk melakukan interpolasi Newton-Gregory maju
    untuk estimasi suhu berdasarkan data historis
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Inisialisasi interpolator dengan data suhu
        
        Args:
            data (pd.DataFrame): DataFrame dengan kolom 'waktu_decimal' dan 'suhu'
        """
        self.data = data.copy().sort_values('waktu_decimal').reset_index(drop=True)
        self.n = len(self.data)
        self.x_values = self.data['waktu_decimal'].values
        self.y_values = self.data['suhu'].values
        
        # Hitung interval (asumsi data dengan interval tetap)
        if self.n > 1:
            self.h = self.x_values[1] - self.x_values[0]
        else:
            self.h = 1.0
            
        # Hitung tabel selisih maju
        self.difference_table = self._calculate_forward_differences()
    
    def _calculate_forward_differences(self) -> np.ndarray:
        """
        Menghitung tabel selisih maju untuk interpolasi Newton-Gregory
        
        Returns:
            np.ndarray: Tabel selisih maju
        """
        # Inisialisasi tabel selisih
        diff_table = np.zeros((self.n, self.n))
        
        # Kolom pertama adalah nilai y
        diff_table[:, 0] = self.y_values
        
        # Hitung selisih maju
        for j in range(1, self.n):
            for i in range(self.n - j):
                diff_table[i, j] = diff_table[i + 1, j - 1] - diff_table[i, j - 1]
        
        return diff_table
    
    def _calculate_binomial_coefficient(self, u: float, n: int) -> float:
        """
        Menghitung koefisien binomial untuk interpolasi Newton-Gregory
        
        Args:
            u (float): Parameter u dalam interpolasi
            n (int): Derajat koefisien
            
        Returns:
            float: Nilai koefisien binomial
        """
        if n == 0:
            return 1.0
        
        result = 1.0
        for i in range(n):
            result *= (u - i) / (i + 1)
        
        return result
    
    def estimate(self, target_time: str) -> float:
        """
        Melakukan estimasi suhu untuk waktu target menggunakan interpolasi Newton-Gregory maju
        
        Args:
            target_time (str): Waktu target dalam format "HH:MM"
            
        Returns:
            float: Estimasi suhu
            
        Raises:
            ValueError: Jika format waktu tidak valid atau data tidak mencukupi
        """
        if self.n < 2:
            raise ValueError("Data tidak mencukupi untuk interpolasi (minimal 2 titik data)")
        
        # Konversi waktu target ke decimal
        try:
            hour, minute = map(int, target_time.split(':'))
            x_target = hour + minute / 60.0
        except:
            raise ValueError(f"Format waktu tidak valid: {target_time}. Gunakan format HH:MM")
        
        # Cari titik data terdekat sebagai titik awal interpolasi
        x0_idx = 0
        min_distance = abs(self.x_values[0] - x_target)
        
        for i in range(1, self.n):
            distance = abs(self.x_values[i] - x_target)
            if distance < min_distance:
                min_distance = distance
                x0_idx = i
        
        # Pastikan kita menggunakan titik awal yang optimal untuk forward difference
        # Gunakan titik data pertama jika target di dalam rentang
        if x_target >= self.x_values[0] and x_target <= self.x_values[-1]:
            # Cari indeks titik data yang tepat sebelum atau pada target
            for i in range(self.n - 1):
                if self.x_values[i] <= x_target <= self.x_values[i + 1]:
                    x0_idx = i
                    break
        
        # Hitung parameter u
        x0 = self.x_values[x0_idx]
        u = (x_target - x0) / self.h
        
        # Hitung interpolasi Newton-Gregory maju
        result = self.difference_table[x0_idx, 0]  # y0
        
        # Tambahkan suku-suku selisih maju
        max_terms = min(self.n - x0_idx, 6)  # Batasi maksimal 6 suku untuk stabilitas
        
        for i in range(1, max_terms):
            if x0_idx + i < self.n:
                binomial_coef = self._calculate_binomial_coefficient(u, i)
                diff_value = self.difference_table[x0_idx, i]
                result += binomial_coef * diff_value
        
        return result
    
    def estimate_multiple(self, target_times: List[str]) -> List[Tuple[str, float]]:
        """
        Melakukan estimasi suhu untuk beberapa waktu target
        
        Args:
            target_times (List[str]): List waktu target dalam format "HH:MM"
            
        Returns:
            List[Tuple[str, float]]: List tuple (waktu, estimasi_suhu)
        """
        results = []
        for time_str in target_times:
            try:
                estimated_temp = self.estimate(time_str)
                results.append((time_str, estimated_temp))
            except Exception as e:
                print(f"Error estimating temperature for {time_str}: {str(e)}")
                # Tetap tambahkan dengan nilai NaN jika gagal
                results.append((time_str, np.nan))
        
        return results
    
    def get_difference_table(self) -> pd.DataFrame:
        """
        Mendapatkan tabel selisih maju dalam format DataFrame untuk visualisasi
        
        Returns:
            pd.DataFrame: Tabel selisih maju
        """
        # Buat header kolom
        columns = ['y'] + [f'Δ^{i}y' for i in range(1, self.n)]
        
        # Buat DataFrame dari tabel selisih
        df = pd.DataFrame(self.difference_table, columns=columns)
        
        # Tambahkan kolom waktu
        df.insert(0, 'Waktu', self.data['waktu'].values)
        
        # Ganti nilai 0 dengan NaN untuk tampilan yang lebih bersih
        for col in columns:
            df[col] = df[col].replace(0, np.nan)
        
        return df
    
    def get_interpolation_info(self) -> dict:
        """
        Mendapatkan informasi tentang interpolasi yang dilakukan
        
        Returns:
            dict: Informasi interpolasi
        """
        return {
            'jumlah_data': self.n,
            'interval': self.h,
            'rentang_waktu': f"{self.data['waktu'].iloc[0]} - {self.data['waktu'].iloc[-1]}",
            'rentang_suhu': f"{self.y_values.min():.1f}°C - {self.y_values.max():.1f}°C",
            'metode': 'Newton-Gregory Forward Interpolation'
        }
    
    def validate_extrapolation_risk(self, target_time: str) -> dict:
        """
        Mengevaluasi risiko ekstrapolasi untuk waktu target
        
        Args:
            target_time (str): Waktu target dalam format "HH:MM"
            
        Returns:
            dict: Informasi risiko ekstrapolasi
        """
        try:
            hour, minute = map(int, target_time.split(':'))
            x_target = hour + minute / 60.0
        except:
            return {'error': 'Format waktu tidak valid'}
        
        x_min, x_max = self.x_values.min(), self.x_values.max()
        
        if x_min <= x_target <= x_max:
            return {
                'status': 'interpolation',
                'risk': 'low',
                'message': 'Target waktu berada dalam rentang data (interpolasi)'
            }
        elif x_target < x_min:
            distance = x_min - x_target
            return {
                'status': 'extrapolation_backward',
                'risk': 'high' if distance > self.h * 2 else 'medium',
                'message': f'Ekstrapolasi mundur {distance:.2f} jam dari data pertama'
            }
        else:  # x_target > x_max
            distance = x_target - x_max
            return {
                'status': 'extrapolation_forward',
                'risk': 'high' if distance > self.h * 2 else 'medium',
                'message': f'Ekstrapolasi maju {distance:.2f} jam dari data terakhir'
            }