import numpy as np
from scipy import signal

# Frequência de amostragem
Fs = 5e3

# Coeficientes do numerador e denominador de C(s)
num = [5.419e-06, 3.523]
den = [1.0, 0.0]

# Discretização por Tustin (bilinear)
b, a = signal.bilinear(num, den, fs=Fs)

# Normalização pelo termo a[0] (garante que a[0] = 1)
b = b / a[0]
a = a / a[0]

# Coeficientes
b0, b1 = b[0], b[1]
a1 = a[1]

# Equação de diferenças para controlador de 1ª ordem
print("\nEquação de diferenças do Controlador:")
print(f"u[k] = {-a1} * u[k-1] + {b0} * e[k] + {b1} * e[k-1]")