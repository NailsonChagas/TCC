import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import control as ct
import time

# ============================================================
# DEFINIÇÃO DO SISTEMA E PARÂMETROS
# ============================================================
s = ct.TransferFunction.s

Vs = 50
L = 0.0083 # 0.008333333333333333
C = 5e-05

# Variação de Potência: de 10% a 100% 
# (Usando 100 pontos para criar um degradê suave no colormap)
potencias = np.linspace(10, 100, 1000) # np.linspace(10, 100, 1000)

# Controlador (Cp)
Cp = (7.0925e-06 * (s + 5.789e04)) / s

# Filtro (Hvd)
Hvd = 9869604.40108936 / (s**2 + 5441.39809270 * s + 9869604.40108936)

# Vetor de tempo para a simulação (0 a 1s)
t = np.linspace(0, 0.4, 1000)

# Estruturas para armazenar os resultados
n_total = len(potencias)
respostas = np.full((n_total, len(t)), np.nan)

polos_re, polos_im = [], []
zeros_re, zeros_im = [], []

# ============================================================
# LOOP DE CÁLCULO
# ============================================================
print("\nIniciando simulações...")
inicio_total = time.perf_counter()

for i, pot in enumerate(potencias):
    # Resistência de carga
    R = 41.7 / (pot / 100.0) # 41.666666666666664 / (pot / 100.0)
    
    # Planta (Gvd)
    Gvd = (Vs / (L*C)) / (s**2 + s/(R*C) + 1/(L*C))
    
    # Sistema em Malha Fechada: T = feedback(Cp * Gvd, Hvd)
    L_loop = Cp * Gvd
    T = ct.feedback(L_loop, Hvd)
    
    # Otimiza a função de transferência cortando polos/zeros redundantes
    T = ct.minreal(T, verbose=False)
    
    # Resposta ao degrau
    _, y = ct.step_response(T, T=t)
    respostas[i, :] = y
    
    # Polos
    poles = ct.poles(T)
    polos_re.append(np.real(poles))
    polos_im.append(np.imag(poles))
    
    # Zeros
    zeros = ct.zeros(T)
    zeros_re.append(np.real(zeros))
    zeros_im.append(np.imag(zeros))

print(f"Tempo total de cálculo: {time.perf_counter() - inicio_total:.2f} s")

# ============================================================
# MAPAS DE CORES E SCALAR MAPPABLES
# ============================================================
FATOR_ESCURO = 0.91

def escurecer_cmap(cmap_original, fator, n=256):
    cores = cmap_original(np.linspace(0, 1, n))
    cores[:, :3] = np.clip(cores[:, :3] * fator, 0, 1)
    return mcolors.LinearSegmentedColormap.from_list(f"{cmap_original.name}_dark_{fator}", cores)

norm = mcolors.Normalize(vmin=min(potencias), vmax=max(potencias))

# Paletas de cores
cmap_step = escurecer_cmap(plt.cm.jet_r, FATOR_ESCURO)
cmap_poles = escurecer_cmap(plt.cm.YlOrBr, 1)
cmap_zeros = escurecer_cmap(plt.cm.inferno_r, 1)

sm_step = cm.ScalarMappable(cmap=cmap_step, norm=norm)
sm_poles = cm.ScalarMappable(cmap=cmap_poles, norm=norm)
sm_zeros = cm.ScalarMappable(cmap=cmap_zeros, norm=norm)

for sm in [sm_step, sm_poles, sm_zeros]:
    sm.set_array([])

# ============================================================
# CRIAÇÃO DAS FIGURAS
# ============================================================
fig1, ax1 = plt.subplots(figsize=(8, 5))
fig2, ax2 = plt.subplots(figsize=(8, 5))

print("\nGerando gráficos...")
for i, pot in enumerate(potencias):
    # Associa a cor exata baseado no colormap atualizado
    c_step = cmap_step(norm(pot))
    c_pole = cmap_poles(norm(pot))
    c_zero = cmap_zeros(norm(pot))
    
    # Plot da Resposta ao degrau
    ax1.plot(t, respostas[i], color=c_step, alpha=0.6)
    
    # Plot dos Polos
    ax2.scatter(polos_re[i], polos_im[i], marker='x', s=45, color=c_pole, alpha=0.7)
    
    # Plot dos Zeros
    if len(zeros_re[i]) > 0:
        ax2.scatter(
            zeros_re[i], zeros_im[i], 
            marker='o', facecolors='none', 
            edgecolors=c_zero, linewidths=1.8, 
            s=65, alpha=0.85
        )

# ============================================================
# FIGURA 1 — RESPOSTA AO DEGRAU
# ============================================================
ax1.set_xlabel("Tempo [s]")
ax1.set_ylabel("Amplitude")
ax1.grid(True)

cbar1 = fig1.colorbar(sm_step, ax=ax1)
cbar1.set_label('Variação da Potência Nominal (%)')

# ============================================================
# FIGURA 2 — POLOS E ZEROS
# ============================================================
ax2.axhline(0, color='black', linewidth=0.8)
ax2.axvline(0, color='black', linewidth=0.8)
ax2.set_xlabel("Parte Real [rad/s]")
ax2.set_ylabel("Parte Imaginária [rad/s]")
ax2.grid(True)

cbar2_p = fig2.colorbar(sm_poles, ax=ax2, pad=0.02)
cbar2_p.set_label('Escala da Potência Nominal (%) - Polos [x]')

cbar2_z = fig2.colorbar(sm_zeros, ax=ax2, pad=0.09)
cbar2_z.set_label('Escala da Potência Nominal (%) - Zeros [o]')

# ============================================================
# AJUSTE E EXPORTAÇÃO
# ============================================================
fig1.tight_layout()
fig2.tight_layout()

fig1.savefig("resposta_degrau_atualizada.png", dpi=500, bbox_inches="tight")
fig2.savefig("polos_e_zeros_atualizados.png", dpi=500, bbox_inches="tight")

plt.show()