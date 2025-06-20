import numpy as np
import pandas as pd

class NewtonGregoryInterpolasi:
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
        
        # Simpan detail perhitungan
        self.calculation_details = []
    
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
    
    def get_difference_table(self):
        """Dapatkan tabel selisih maju dalam format DataFrame"""
        columns = ['y'] + [f'Δ^{i}y' for i in range(1, self.n)]
        
        # Buat tabel dengan NaN untuk sel kosong
        table_display = np.full((self.n, self.n), np.nan)
        for i in range(self.n):
            for j in range(self.n - i):
                table_display[i, j] = self.diff_table[i, j]
        
        df_table = pd.DataFrame(table_display, columns=columns[:self.n])
        df_table.index = [f'x{i}' for i in range(self.n)]
        df_table['Waktu'] = self.data['waktu'].values
        df_table['Suhu'] = self.data['suhu'].values
        
        # Reorder columns
        cols = ['Waktu', 'Suhu'] + [col for col in df_table.columns if col not in ['Waktu', 'Suhu']]
        return df_table[cols]
    
    def estimate_with_details(self, target_time):
        """Estimasi suhu untuk waktu target dengan detail perhitungan"""
        if self.n < 2:
            raise ValueError("Minimal 2 titik data diperlukan")
        
        # Reset detail perhitungan
        self.calculation_details = []
        
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
        
        # Simpan detail awal
        self.calculation_details.append({
            'step': 'Parameter Dasar',
            'description': f'x₀ = {x0:.2f}, h = {self.h:.2f}, u = (x - x₀)/h = ({x_target:.2f} - {x0:.2f})/{self.h:.2f} = {u:.4f}',
            'value': u
        })
        
        # Interpolasi Newton-Gregory
        result = self.diff_table[x0_idx, 0]  # y0
        
        self.calculation_details.append({
            'step': 'Suku ke-0',
            'description': f'y₀ = {result:.4f}',
            'value': result
        })
        
        # Tambahkan suku-suku berikutnya
        max_terms = min(self.n - x0_idx, 5)  # Batasi untuk stabilitas
        total_correction = 0
        
        for i in range(1, max_terms):
            if x0_idx + i < self.n:
                coeff = self._binomial_coeff(u, i)
                diff = self.diff_table[x0_idx, i]
                correction = coeff * diff
                total_correction += correction
                
                # Format binomial coefficient
                binom_str = self._format_binomial(u, i)
                
                self.calculation_details.append({
                    'step': f'Suku ke-{i}',
                    'description': f'{binom_str} × Δ^{i}y₀ = {coeff:.6f} × {diff:.4f} = {correction:.6f}',
                    'value': correction
                })
        
        final_result = result + total_correction
        
        self.calculation_details.append({
            'step': 'Hasil Akhir',
            'description': f'y = {result:.4f} + {total_correction:.6f} = {final_result:.4f}',
            'value': final_result
        })
        
        return final_result
    
    def _format_binomial(self, u, n):
        """Format koefisien binomial untuk tampilan"""
        if n == 1:
            return f'u'
        elif n == 2:
            return f'u(u-1)/2!'
        elif n == 3:
            return f'u(u-1)(u-2)/3!'
        else:
            terms = '×'.join([f'(u-{i})' for i in range(n)])
            return f'u×{terms}/{n}!'
    
 