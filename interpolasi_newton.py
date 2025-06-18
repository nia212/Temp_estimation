import numpy as np
import pandas as pd

class NewtonGregoryInterpolator:
    """Interpolasi Newton-Gregory maju untuk estimasi suhu"""
    
    def __init__(self, data):
        self.data = data.copy().sort_values('waktu_decimal').reset_index(drop=True)
        self.x = self.data['waktu_decimal'].values
        self.y = self.data['suhu'].values
        self.n = len(self.data)
        
        # Hitung interval
        self.h = self.x[1] - self.x[0] if self.n > 1 else 1.0
        
        # Hitung tabel selisih maju
        self.diff_table = self._calculate_differences()
    
    def _calculate_differences(self):
        """Hitung tabel selisih maju"""
        table = np.zeros((self.n, self.n))
        table[:, 0] = self.y
        
        for j in range(1, self.n):
            for i in range(self.n - j):
                table[i, j] = table[i + 1, j - 1] - table[i, j - 1]
        
        return table
    
    def _binomial_coeff(self, u, n):
        """Hitung koefisien binomial"""
        if n == 0:
            return 1.0
        result = 1.0
        for i in range(n):
            result *= (u - i) / (i + 1)
        return result
    
    def estimate(self, target_time):
        """Estimasi suhu untuk waktu target"""
        if self.n < 2:
            raise ValueError("Minimal 2 titik data diperlukan")
        
        # Konversi waktu ke decimal
        try:
            hour, minute = map(int, target_time.split(':'))
            x_target = hour + minute / 60.0
        except:
            raise ValueError(f"Format waktu tidak valid: {target_time}")
        
        # Cari titik referensi
        x0_idx = 0
        for i in range(self.n - 1):
            if self.x[i] <= x_target <= self.x[i + 1]:
                x0_idx = i
                break
        
        # Hitung parameter u
        x0 = self.x[x0_idx]
        u = (x_target - x0) / self.h
        
        # Interpolasi Newton-Gregory
        result = self.diff_table[x0_idx, 0]  # y0
        
        # Tambahkan suku-suku berikutnya
        max_terms = min(self.n - x0_idx, 5)  # Batasi untuk stabilitas
        
        for i in range(1, max_terms):
            if x0_idx + i < self.n:
                coeff = self._binomial_coeff(u, i)
                diff = self.diff_table[x0_idx, i]
                result += coeff * diff
        
        return result