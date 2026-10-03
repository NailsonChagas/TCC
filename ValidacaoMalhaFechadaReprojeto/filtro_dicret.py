import numpy as np
from scipy import signal

# Frequência de amostragem
Fs = 50e3

# Função de transferência H(s)
num = [9.87e8]
den = [1, 5.441e4, 9.87e8]

# Discretização por Tustin
b, a = signal.bilinear(num, den, fs=Fs)

# Normalização
b = b / a[0]
a = a / a[0]

# Coeficientes
b0, b1, b2 = b
a1, a2 = a[1], a[2]

# Equação de diferenças
print("\nEquação de diferenças:")
print(
    f"y[k] = {-a1}*y[k-1] "
    f"{-a2}*y[k-2] "
    f"{b0}*x[k] "
    f"{b1}*x[k-1] "
    f"{b2}*x[k-2]"
)