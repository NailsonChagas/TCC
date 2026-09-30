import numpy as np
from scipy.linalg import expm
import config as cfg

def simulate_buck_open_loop(n, d_val):
    """Roda a simulação ZOH do conversor Buck em laço aberto com Duty Cycle fixo."""
    timestep = cfg.BASE_TIME_STEP / n
    n_points = int(cfg.MAX_SIM_TIME / timestep)
    t_sim = np.arange(n_points) * timestep

    # Matrizes de espaço de estados
    A = np.array([[0, -1/cfg.L], [1/cfg.C, -1/(cfg.R*cfg.C)]])
    B1 = np.array([[1/cfg.L], [0]]) # Chave fechada
    B2 = np.array([[0], [0]])       # Chave aberta

    # Discretização ZOH
    Ad = expm(A * timestep)
    A_inv = np.linalg.inv(A)
    Bd1 = A_inv @ (Ad - np.eye(2)) @ B1
    Bd2 = A_inv @ (Ad - np.eye(2)) @ B2

    coeffs = {
        'Ad_00': Ad[0, 0], 'Ad_01': Ad[0, 1],
        'Ad_10': Ad[1, 0], 'Ad_11': Ad[1, 1],
        'Bd1_00_Vs': Bd1[0, 0] * cfg.V_S, 'Bd1_10_Vs': Bd1[1, 0] * cfg.V_S,
        'Bd2_00_Vs': Bd2[0, 0] * cfg.V_S, 'Bd2_10_Vs': Bd2[1, 0] * cfg.V_S,
        'timestep': timestep,
        'n_points': n_points
    }

    iL = np.zeros(n_points)
    vC = np.zeros(n_points)

    for k in range(n_points - 1):
        is_sw_closed = (k % n) < (d_val * n)
        B_active = Bd1 if is_sw_closed else Bd2
        
        iL[k + 1] = Ad[0, 0] * iL[k] + Ad[0, 1] * vC[k] + B_active[0, 0]
        vC[k + 1] = Ad[1, 0] * iL[k] + Ad[1, 1] * vC[k] + B_active[1, 0]

    return t_sim, vC, iL, coeffs