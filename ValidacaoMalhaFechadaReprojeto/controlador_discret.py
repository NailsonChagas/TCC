import numpy as np
from scipy import signal

# Frequência de amostragem (exemplo: 50 kHz ou a frequência do seu sistema)
Fs = 50e3

# Coeficientes do numerador e denominador de Cp(s)
# Cp(s) = (0.001033*s + 67.15) / (1*s + 0)
num = [0.001033, 67.15]
den = [1.0, 0.0]

# Discretização por Tustin (bilinear)
b, a = signal.bilinear(num, den, fs=Fs)

# Normalização pelo termo a[0] (garante que a[0] = 1)
b = b / a[0]
a = a / a[0]

# Coeficientes (para um sistema de 1ª ordem, teremos b0, b1 e a1)
b0, b1 = b[0], b[1]
a1 = a[1]

# Equação de diferenças para controlador de 1ª ordem:
# y[k] = -a1*y[k-1] + b0*x[k] + b1*x[k-1]
print("\nEquação de diferenças do Controlador:")
print(
    f"u[k] = {-a1:.6f} * u[k-1] + "
    f"{b0:.6f} * e[k] + "
    f"{b1:.6f} * e[k-1]"
)