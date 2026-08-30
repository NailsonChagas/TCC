import matplotlib.pyplot as plt
import control as ct
import numpy as np

from aux_graph import plot_root_locus_matlab, plot_specification_region

s = ct.TransferFunction.s

# Funções de transferência originais
G = 1.984e11 / (s**2 + 1.332e5*s + 3.968e9) # Planta (Buck CCM)
H = 9.87e8 / (s**2 + 5.441e4*s + 9.87e8)    # Filtro antialiasing

# 1. Definição do Polo Dominante Desejado (sd) a partir dos requisitos
zeta = 0.69
wn = 11.59e3
sd = -zeta * wn + 1j * wn * np.sqrt(1 - zeta**2)

# 2. Avaliação da malha aberta não compensada no ponto sd
L_uncomp = G * H
L_sd = L_uncomp(sd) # Avalia a magnitude e fase do sistema original no ponto sd

# 3. Aplicação da Condição de Ângulo para encontrar o zero do PI
angle_L_sd = np.angle(L_sd) # Soma das contribuições angulares da planta + filtro
angle_sd = np.angle(sd)     # Contribuição angular do polo na origem do PI (s = 0)

# Cálculo da deficiência angular (forçando a soma a atingir -180 graus)
angle_zero = np.pi + angle_sd - angle_L_sd
angle_zero = (angle_zero + np.pi) % (2 * np.pi) - np.pi # Ajuste para o quadrante principal

# Posição do zero (z_pi) alocada no eixo real via trigonometria
z_pi = abs(np.real(sd)) + np.imag(sd) / np.tan(angle_zero)

# 4. Aplicação da Condição de Magnitude para isolar Kp e calcular Ki
# O ganho Kp força a equação: |Kp| * |(sd + z_pi) / sd| * |L_sd| = 1
C_unscaled_sd = (sd + z_pi) / sd
KP = 1.0 / (np.abs(C_unscaled_sd) * np.abs(L_sd))
KI = KP * z_pi

# 5. Construção do Controlador C(s) projetado e da Malha Fechada
C = KP * ((s + z_pi) / s)
L = G * H * C

print(f"Polo Desejado (sd): {sd:.2f}")
print(f"Posição do Zero do PI: {-z_pi:.2f}")
print(f"Parâmetros calculados: KP = {KP:.6f}, KI = {KI:.2f}")
print(f"\nControlador C(s):\n{C}")
print(f"Malha aberta L(s):\n{L}")

# Plotagem do Lugar das Raízes validando o cruzamento sobre a região admissível
fig, ax = plot_root_locus_matlab(L)
plot_specification_region(ax, zeta_min=zeta, sigma_min=zeta*wn)
fig.savefig('lr_pi_calculado.png', dpi=400, bbox_inches='tight')
plt.show()
plt.close('all')

print(f"Kp: {KP}")
print(f"Ki: {KI}")