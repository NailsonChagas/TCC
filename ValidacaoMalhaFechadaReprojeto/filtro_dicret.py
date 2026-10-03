import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

# Constantes de Estilização
FONT_TITLE = 16    
FONT_LABEL = 13    
FONT_TICKS = 12    
FONT_LEGEND = 13 
DPI = 200    

# Frequência de amostragem e frequência de corte
Fs = 5e3
Fc = Fs / 10.0  # Frequência de corte do filtro (ex: 500 Hz)

# Função de transferência H(s) do filtro contínuo
num = [9.87e06]
den = [1.0, 5441, 9.87e06]

# 1. Geração do Diagrama de Bode do sistema contínuo
sys_cont = signal.TransferFunction(num, den)
# Vetor de frequências de 10^0 Hz até 10^6 Hz (para abranger Fc e Fs adequadamente)
w_vec = np.logspace(0, 6, 2000) * 2 * np.pi
w, mag, phase = signal.bode(sys_cont, w=w_vec)
freq_hz = w / (2 * np.pi)

# 2. Plotagem do Diagrama de Bode com marcações de Fc e Fs
plt.figure(figsize=(9, 7), dpi=DPI)

# Subplot de Magnitude
plt.subplot(2, 1, 1)
plt.semilogx(freq_hz, mag, color='blue', linewidth=2, label='Magnitude H(s)')
plt.axvline(Fc, color='darkorange', linestyle='--', linewidth=1.5, label=f'Fc = {Fc/1e3:.1f} kHz')
plt.axvline(Fs, color='red', linestyle=':', linewidth=1.5, label=f'Fs = {Fs/1e3:.1f} kHz')
plt.axhline(-40, color='gray', linestyle='-.', linewidth=1.2, label='Atenuação -40 dB')
plt.ylabel('Magnitude (dB)', fontsize=FONT_LABEL)
plt.grid(True, which="both", linestyle='--', alpha=0.6)
plt.legend(loc='lower left', fontsize=FONT_LEGEND)
plt.tick_params(axis='both', labelsize=FONT_TICKS)

# Subplot de Fase
plt.subplot(2, 1, 2)
plt.semilogx(freq_hz, phase, color='crimson', linewidth=2, label='Fase H(s)')
plt.axvline(Fc, color='darkorange', linestyle='--', linewidth=1.5, label=f'Fc = {Fc/1e3:.1f} kHz')
plt.axvline(Fs, color='red', linestyle=':', linewidth=1.5, label=f'Fs = {Fs/1e3:.1f} kHz')
plt.ylabel('Fase (graus)', fontsize=FONT_LABEL)
plt.xlabel('Frequência (Hz)', fontsize=FONT_LABEL)
plt.grid(True, which="both", linestyle='--', alpha=0.6)
plt.legend(loc='lower left', fontsize=FONT_LEGEND)
plt.tick_params(axis='both', labelsize=FONT_TICKS)

plt.tight_layout()
output_filename = "img/bode_filtro_continuo.png"
plt.savefig(output_filename, dpi=DPI)
plt.show()
print(f"Gráfico de Bode salvo em '{output_filename}' com DPI={DPI}.\n")

# 3. Discretização por Tustin
b, a = signal.bilinear(num, den, fs=Fs)

# Normalização
b = b / a[0]
a = a / a[0]

# Coeficientes
b0, b1, b2 = b
a1, a2 = a[1], a[2]

# Equação de diferenças
print("Equação de diferenças:")
print(
    f"y[k] = {-a1}*y[k-1] "
    f"{-a2}*y[k-2] "
    f"{b0}*x[k] "
    f"{b1}*x[k-1] "
    f"{b2}*x[k-2]"
)