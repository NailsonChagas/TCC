import numpy as np
from scipy.linalg import expm
import matplotlib.pyplot as plt

# --- CONFIG DA SIM ---
F_MULTIPLIER = 100
T_END = 0.006  # Tempo total de 6ms

# --- PARÂMETROS DO SISTEMA ---
Fs = 50e3        # Frequência de chaveamento [Hz]
L = 1.5e-3       # Indutância [H]
R = 41.7         # Resistência de carga [Ohm]
C = 0.18e-6      # Capacitância [F]
Ts = 1 / Fs

Tsim = 1 / (F_MULTIPLIER * Fs)
n_points = int(T_END / Tsim)
t = np.arange(n_points) * Tsim 

# --- VETORES DE ENTRADA E REFERÊNCIA ---
# Tensão de entrada (agora um vetor para permitir Vs[k] + Vs[k+1]) Degrau na metade da sim (50V -> 60V)
Vs_array = np.full(n_points, 50.0)
idx_step = int((T_END/2) / Tsim)
Vs_array[idx_step:] = 60.0

# Referência: 25 V
V_ref = 25

# --- CONSTANTES E MATRIZES DE DISCRETIZAÇÃO ---
# 1. ZOH (Exato via Matriz Exponencial)
A = np.array([[0, -1/L], [1/C, -1/(R*C)]])
B1 = np.array([1/L, 0])
Ad = expm(A * Tsim)
A_inv = np.linalg.inv(A)
Bd1 = A_inv @ (Ad - np.eye(2)) @ B1  

# 2. Euler (Aproximação linear)
ke1 = Tsim / L
ke2 = Tsim / C
ke3 = 1 - (Tsim / (R * C))

# 3. Trapézio (Tustin)
Delta = 4*C*L*R + 2*L*Tsim + R*(Tsim**2)    
kt1 = (4*C*L*R + 2*L*Tsim - R*(Tsim**2)) / Delta
kt2 = (4*C*R*Tsim) / Delta
kt3 = (Tsim**2 + 2*C*R*Tsim) / Delta
kt4 = (4*L*R*Tsim) / Delta
kt5 = (4*C*L*R - 2*L*Tsim - R*(Tsim**2)) / Delta
kt6 = (R*(Tsim**2)) / Delta

# --- COMPONENTES DA MALHA DE CONTROLE ---
def filter_step(x_k, x_k1, x_k2, y_k1, y_k2):
    y_k = (1.09727 * y_k1) - (0.33759 * y_k2) + \
          (0.06008 * x_k) + (0.12016 * x_k1) + (0.06008 * x_k2)
    return y_k

def controller_step(e_k, e_k1, u_k1):
    u_k = u_k1 + (0.001906 * e_k) + (0.00049680633 * e_k1)
    return u_k

# --- FUNÇÃO DE SIMULAÇÃO ---
def run_simulation(method):
    iL = np.zeros(n_points)
    vC = np.zeros(n_points)
    D_array = np.zeros(n_points)

    e_k, e_k1 = 0.0, 0.0
    u_k1 = 0.0 # não sei se começo o duty cycle em 0 ou 0.5 -> pastU
    x_k, x_k1, x_k2 = 0.0, 0.0, 0.0
    y_k1, y_k2 = 0.0, 0.0
    D = u_k1

    for k in range(n_points - 1):
        is_switch_closed = (k % F_MULTIPLIER) < (D * F_MULTIPLIER)
        
        if method == 'zoh':
            if is_switch_closed:
                iL[k+1] = Ad[0,0]*iL[k] + Ad[0,1]*vC[k] + Bd1[0]*Vs_array[k]
                vC[k+1] = Ad[1,0]*iL[k] + Ad[1,1]*vC[k] + Bd1[1]*Vs_array[k]
            else:
                iL[k+1] = Ad[0,0]*iL[k] + Ad[0,1]*vC[k]
                vC[k+1] = Ad[1,0]*iL[k] + Ad[1,1]*vC[k]
                
        elif method == 'euler':
            if is_switch_closed:
                iL[k+1] = iL[k] - ke1 * vC[k] + ke1 * Vs_array[k]
                vC[k+1] = ke2 * iL[k] + ke3 * vC[k]
            else:
                iL[k+1] = iL[k] - ke1 * vC[k]
                vC[k+1] = ke2 * iL[k] + ke3 * vC[k]
                
        elif method == 'trapezium':
            if is_switch_closed:
                # Substituição de 2*Vs por (Vs_array[k] + Vs_array[k+1])
                iL[k+1] = kt1 * iL[k] - kt2 * vC[k] + kt3 * (Vs_array[k] + Vs_array[k+1])
                vC[k+1] = kt4 * iL[k] + kt5 * vC[k] + kt6 * (Vs_array[k] + Vs_array[k+1])
            else:
                iL[k+1] = kt1 * iL[k] - kt2 * vC[k]
                vC[k+1] = kt4 * iL[k] + kt5 * vC[k]

        # 2. Atualização do Filtro e Controle
        if (k + 1) % F_MULTIPLIER == 0:
            x_k2 = x_k1
            x_k1 = x_k
            x_k = vC[k+1]
            
            y_k = filter_step(x_k, x_k1, x_k2, y_k1, y_k2)
            
            y_k2 = y_k1
            y_k1 = y_k
            
            e_k1 = e_k
            e_k = V_ref - y_k
            
            D = controller_step(e_k, e_k1, u_k1)
            
            if D > 1.0: D = 1.0
            elif D < 0.0: D = 0.0
            
            u_k1 = D
            
        D_array[k+1] = D

    return iL, vC, D_array

# --- EXECUTANDO AS SIMULAÇÕES ---
iL_zoh, vC_zoh, D_zoh = run_simulation('zoh')
iL_eul, vC_eul, D_eul = run_simulation('euler')
iL_trap, vC_trap, D_trap = run_simulation('trapezium')

# --- PLOTAGEM DOS RESULTADOS ---
matlab_blue   = '#0072BD'
matlab_orange = '#D95319'
matlab_green  = '#77AC30'
matlab_red    = '#A2142F'

fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(12, 12), sharex=True)

# 1. Tensão de entrada
ax1.plot(t * 1000, Vs_array, color=matlab_red, alpha=0.7)
ax1.set_ylabel(r'$v_S$ [V]')
ax1.grid(True)

# 2. Tensão no Capacitor (vC)
ax2.plot(t * 1000, vC_zoh, label='ZOH', color=matlab_blue, alpha=0.7)
ax2.plot(t * 1000, vC_trap, label='Trapézio', color=matlab_green, alpha=0.7)
ax2.plot(t * 1000, vC_eul, label='Euler', color=matlab_orange, alpha=0.7)
ax2.axhline(V_ref, color=matlab_red, linestyle=':', linewidth=2, label=f'Referência ({V_ref}V)')
ax2.set_ylabel(r'$v_C$ [V]')
ax2.legend(loc='lower right')
ax2.grid(True)

# 3. Corrente no Indutor (iL)
ax3.plot(t * 1000, iL_zoh, label='ZOH', color=matlab_blue, alpha=0.7)
ax3.plot(t * 1000, iL_trap, label='Trapézio', color=matlab_green, alpha=0.7)
ax3.plot(t * 1000, iL_eul, label='Euler', color=matlab_orange, alpha=0.7)
ax3.set_ylabel(r'$i_L$ [A]')
ax3.legend(loc='upper right')
ax3.grid(True)

# 4. Razão Cíclica (Duty Cycle - D)
ax4.step(t * 1000, D_zoh, label='ZOH', color=matlab_blue, where='post', alpha=0.7)
ax4.step(t * 1000, D_trap, label='Trapézio', color=matlab_green, where='post', alpha=0.7)
ax4.step(t * 1000, D_eul, label='Euler', color=matlab_orange, where='post', alpha=0.7)
ax4.axhline(0.5, color='gray', linestyle=':', linewidth=2, label='0,5')
ax4.set_xlabel('Tempo [ms]')
ax4.set_ylabel('Razão Cíclica')
ax4.set_ylim(0, 1)
ax4.legend(loc='upper right')
ax4.grid(True)

plt.tight_layout()
plt.show()