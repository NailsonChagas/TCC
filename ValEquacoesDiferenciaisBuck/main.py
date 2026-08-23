import numpy as np
import matplotlib.pyplot as plt
  
# ==========================================================
# VARIÁVEIS DE CONFIGURAÇÃO DE FONTES
# ==========================================================
FONT_TITLE = 15    # Tamanho da fonte dos títulos dos subgráficos
FONT_LABEL = 13    # Tamanho da fonte dos rótulos dos eixos X e Y
FONT_TICKS = 12    # Tamanho da fonte dos números (ticks) dos eixos X e Y
FONT_LEGEND = 13 # Tamanho da fonte da legenda
DPI = 500 # Resolução padrão para salvar as imagens
    

# Dentro do arquivo buck.csv tenho o resultado de uma simulação 
# feita com os seguintes parametros:
# .tran 0 1m 0 20n
# as 3 primeiras linhas são assim
# "Time","V(n02)","I(L1)"
# 0,2.0015322977629,0.0479983764451534
# 3.2e-12,2.0015322977629,0.0479983764451534
# no QSpice do conversor buck descrito abaixo:

# Parametros do conversor buck
Vs = 50          # Tensão de entrada [V]
Fs = 50e3        # Frequência de chaveamento [Hz]
D = 0.50         # Razão cíclica [adimensional]
L = 1.5e-3       # Indutância [H]
R = 41.7         # Resistência de carga [Ohm]
C = 0.18e-6      # Capacitância [F]
Ts = 1 / Fs

F_MULTIPLIER = [5, 10, 20, 30, 40, 50, 100]
t_end = 0.0010 # tempo total da sim (1ms)

def buck_euler_discretization(n):
    Tsim = 1 / (n * Fs)
    n_points = int(t_end/Tsim) # total de pontos

    ke1 = Tsim / L
    ke2 = Tsim / C
    ke3 = 1 - (Tsim / (R * C))

    # vetores de estados
    iL = np.zeros(n_points)
    vC = np.zeros(n_points)
    t = np.linspace(0, t_end, n_points)

    for k in range(n_points - 1):
        if (t[k] % Ts) < (D * Ts): # chave fechada
            iL[k+1] = iL[k] - ke1 * vC[k] + ke1 * Vs
            vC[k+1] = ke2 * iL[k] + ke3 * vC[k]
        else: # chave aberta
            iL[k+1] = iL[k] - ke1 * vC[k]
            vC[k+1] = ke2 * iL[k] + ke3 * vC[k]

    return t, iL, vC

def buck_trapezium_discretization(n):
    Tsim = 1 / (n * Fs)
    n_points = int(t_end/Tsim) # total de pontos

    Delta = 4*C*L*R + 2*L*Tsim + R*(Tsim**2)    
    kt1 = (4*C*L*R + 2*L*Tsim - R*(Tsim**2)) / Delta
    kt2 = (4*C*R*Tsim) / Delta
    kt3 = (Tsim**2 + 2*C*R*Tsim) / Delta
    kt4 = (4*L*R*Tsim) / Delta
    kt5 = (4*C*L*R - 2*L*Tsim - R*(Tsim**2)) / Delta
    kt6 = (R*(Tsim**2)) / Delta

    # vetores de estados
    iL = np.zeros(n_points)
    vC = np.zeros(n_points)
    t = np.linspace(0, t_end, n_points)

    for k in range(n_points - 1):
        if (t[k] % Ts) < (D * Ts): # chave fechada
            # como Vs é DC constante, Vs[k] + Vs[k+1] = 2 * Vs
            iL[k+1] = kt1 * iL[k] - kt2 * vC[k] + kt3 * (2 * Vs)
            vC[k+1] = kt4 * iL[k] + kt5 * vC[k] + kt6 * (2 * Vs)
        else: # chave aberta
            iL[k+1] = kt1 * iL[k] - kt2 * vC[k]
            vC[k+1] = kt4 * iL[k] + kt5 * vC[k]

    return t, iL, vC

def plot_erro_relativo_medio(F_MULTIPLIER, t_qs, iL_qs, vC_qs):
    # Listas para armazenar os erros
    err_iL_eul, err_vC_eul = [], []
    err_iL_trap, err_vC_trap = [], []
    
    n_sorted = sorted(F_MULTIPLIER)
    
    for n in n_sorted:
        # Roda as simulações para o 'n' atual
        t_eul, iL_eul, vC_eul = buck_euler_discretization(n)
        t_trap, iL_trap, vC_trap = buck_trapezium_discretization(n)
        
        # Interpola os dados do QSpice para os mesmos instantes de tempo da simulação Python
        iL_qs_interp_eul = np.interp(t_eul, t_qs, iL_qs)
        vC_qs_interp_eul = np.interp(t_eul, t_qs, vC_qs)
        
        iL_qs_interp_trap = np.interp(t_trap, t_qs, iL_qs)
        vC_qs_interp_trap = np.interp(t_trap, t_qs, vC_qs)
        
        # Define um valor epsilon (muito pequeno) para evitar divisão por zero 
        # nos instantes iniciais onde tensão e corrente podem ser nulas.
        eps = 1e-8
        
        # Cálculo do erro percentual relativo médio (MAPE)
        e_iL_eul = np.mean(np.abs((iL_eul - iL_qs_interp_eul) / np.maximum(np.abs(iL_qs_interp_eul), eps))) * 100
        e_vC_eul = np.mean(np.abs((vC_eul - vC_qs_interp_eul) / np.maximum(np.abs(vC_qs_interp_eul), eps))) * 100
        
        e_iL_trap = np.mean(np.abs((iL_trap - iL_qs_interp_trap) / np.maximum(np.abs(iL_qs_interp_trap), eps))) * 100
        e_vC_trap = np.mean(np.abs((vC_trap - vC_qs_interp_trap) / np.maximum(np.abs(vC_qs_interp_trap), eps))) * 100
        
        err_iL_eul.append(e_iL_eul)
        err_vC_eul.append(e_vC_eul)
        err_iL_trap.append(e_iL_trap)
        err_vC_trap.append(e_vC_trap)

    # ==========================================================
    # PLOTAGEM DOS ERROS
    # ==========================================================
    fig, (ax_iL, ax_vC) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Gráfico de Erro da Corrente
    ax_iL.plot(n_sorted, err_iL_eul, marker='o', linestyle='-', label='Euler')
    ax_iL.plot(n_sorted, err_iL_trap, marker='s', linestyle='-', label='Trapézio')
    ax_iL.set_title('Erro Relativo Médio - Corrente $i_L$', fontsize=FONT_TITLE)
    ax_iL.set_xlabel('Fator n', fontsize=FONT_LABEL)
    ax_iL.set_ylabel('Erro (%)', fontsize=FONT_LABEL)
    ax_iL.grid(True)
    ax_iL.legend(fontsize=FONT_LEGEND)
    ax_iL.tick_params(axis='both', labelsize=FONT_TICKS)
    
    # Gráfico de Erro da Tensão
    ax_vC.plot(n_sorted, err_vC_eul, marker='o', linestyle='-', label='Euler')
    ax_vC.plot(n_sorted, err_vC_trap, marker='s', linestyle='-', label='Trapézio')
    ax_vC.set_title('Erro Relativo Médio - Tensão $v_C$', fontsize=FONT_TITLE)
    ax_vC.set_xlabel('Fator n', fontsize=FONT_LABEL)
    ax_vC.set_ylabel('Erro (%)', fontsize=FONT_LABEL)
    ax_vC.grid(True)
    ax_vC.legend(fontsize=FONT_LEGEND)
    ax_vC.tick_params(axis='both', labelsize=FONT_TICKS)
    
    fig.tight_layout()
    fig.savefig('erro_relativo_completo.png', dpi=DPI)

def main():
    # Lista contendo todos os eixos criados para aplicar a formatação padrão de forma limpa
    # (Vamos preencher e configurar depois)
    
    # ==========================================================
    # IMAGENS COMPLETAS (Todo o intervalo de simulação)
    # ==========================================================
    fig_iL, (ax_iL_eul, ax_iL_trap) = plt.subplots(1, 2, figsize=(14, 8))
    
    for ax in [ax_iL_eul, ax_iL_trap]:
        ax.set_ylabel('Corrente [A]', fontsize=FONT_LABEL)
        ax.set_xlabel('Tempo [ms]', fontsize=FONT_LABEL)
        ax.grid(True)
        ax.tick_params(axis='both', labelsize=FONT_TICKS)
        
    ax_iL_eul.set_title('Método de Euler', fontsize=FONT_TITLE)
    ax_iL_trap.set_title('Método do Trapézio', fontsize=FONT_TITLE)

    fig_vC, (ax_vC_eul, ax_vC_trap) = plt.subplots(1, 2, figsize=(14, 8))
    
    for ax in [ax_vC_eul, ax_vC_trap]:
        ax.set_ylabel('Tensão [V]', fontsize=FONT_LABEL)
        ax.set_xlabel('Tempo [ms]', fontsize=FONT_LABEL)
        ax.grid(True)
        ax.tick_params(axis='both', labelsize=FONT_TICKS)
        
    ax_vC_eul.set_title('Método de Euler', fontsize=FONT_TITLE)
    ax_vC_trap.set_title('Método do Trapézio', fontsize=FONT_TITLE)


    # ==========================================================
    # IMAGENS REGIME PERMANENTE
    # ==========================================================
    fig_iL_z, (ax_iL_eul_z, ax_iL_trap_z) = plt.subplots(1, 2, figsize=(14, 8))
    
    for ax in [ax_iL_eul_z, ax_iL_trap_z]:
        ax.set_ylabel('Corrente [A]', fontsize=FONT_LABEL)
        ax.set_xlabel('Tempo [ms]', fontsize=FONT_LABEL)
        ax.grid(True)
        ax.set_xlim(0.2, 0.225)
        ax.tick_params(axis='both', labelsize=FONT_TICKS)
        
    ax_iL_eul_z.set_title('Método de Euler', fontsize=FONT_TITLE)
    ax_iL_trap_z.set_title('Método do Trapézio', fontsize=FONT_TITLE)

    fig_vC_z, (ax_vC_eul_z, ax_vC_trap_z) = plt.subplots(1, 2, figsize=(14, 8))
    
    for ax in [ax_vC_eul_z, ax_vC_trap_z]:
        ax.set_ylabel('Tensão [V]', fontsize=FONT_LABEL)
        ax.set_xlabel('Tempo [ms]', fontsize=FONT_LABEL)
        ax.grid(True)
        ax.set_xlim(0.2, 0.225)
        ax.tick_params(axis='both', labelsize=FONT_TICKS)
        
    ax_vC_eul_z.set_title('Método de Euler', fontsize=FONT_TITLE)
    ax_vC_trap_z.set_title('Método do Trapézio', fontsize=FONT_TITLE)


    # ==========================================================
    # IMAGENS REGIME TRANSITÓRIO
    # ==========================================================
    fig_iL_trans, (ax_iL_eul_trans, ax_iL_trap_trans) = plt.subplots(1, 2, figsize=(14, 8))
    
    for ax in [ax_iL_eul_trans, ax_iL_trap_trans]:
        ax.set_ylabel('Corrente [A]', fontsize=FONT_LABEL)
        ax.set_xlabel('Tempo [ms]', fontsize=FONT_LABEL)
        ax.grid(True)
        ax.set_xlim(0.0, 0.12)
        ax.tick_params(axis='both', labelsize=FONT_TICKS)
        
    ax_iL_eul_trans.set_title('Método de Euler', fontsize=FONT_TITLE)
    ax_iL_trap_trans.set_title('Método do Trapézio', fontsize=FONT_TITLE)

    fig_vC_trans, (ax_vC_eul_trans, ax_vC_trap_trans) = plt.subplots(1, 2, figsize=(14, 8))
    
    for ax in [ax_vC_eul_trans, ax_vC_trap_trans]:
        ax.set_ylabel('Tensão [V]', fontsize=FONT_LABEL)
        ax.set_xlabel('Tempo [ms]', fontsize=FONT_LABEL)
        ax.grid(True)
        ax.set_xlim(0.0, 0.12)
        ax.tick_params(axis='both', labelsize=FONT_TICKS)
        
    ax_vC_eul_trans.set_title('Método de Euler', fontsize=FONT_TITLE)
    ax_vC_trap_trans.set_title('Método do Trapézio', fontsize=FONT_TITLE)


    # ==========================================================
    # CARREGAMENTO DOS DADOS DO QSPICE
    # ==========================================================
    qspice_data = np.loadtxt('buck.csv', delimiter=',', skiprows=1)
    t_qs = qspice_data[:, 0]  
    vC_qs = qspice_data[:, 1] 
    iL_qs = qspice_data[:, 2] 

    plot_erro_relativo_medio(F_MULTIPLIER, t_qs, iL_qs, vC_qs)

    # ==========================================================
    # EXECUÇÃO E PLOTAGEM
    # ==========================================================
    for n in sorted(F_MULTIPLIER):
        t_eul, iL_eul, vC_eul = buck_euler_discretization(n)
        t_trap, iL_trap, vC_trap = buck_trapezium_discretization(n)
        
        # Plota completos
        ax_iL_eul.plot(t_eul * 1000, iL_eul, label=f'n={n}', alpha=0.8)
        ax_iL_trap.plot(t_trap * 1000, iL_trap, label=f'n={n}', alpha=0.8)
        ax_vC_eul.plot(t_eul * 1000, vC_eul, label=f'n={n}', alpha=0.8)
        ax_vC_trap.plot(t_trap * 1000, vC_trap, label=f'n={n}', alpha=0.8)

        # Plota permanente (zoom)
        ax_iL_eul_z.plot(t_eul * 1000, iL_eul, label=f'n={n}', alpha=0.8)
        ax_iL_trap_z.plot(t_trap * 1000, iL_trap, label=f'n={n}', alpha=0.8)
        ax_vC_eul_z.plot(t_eul * 1000, vC_eul, label=f'n={n}', alpha=0.8)
        ax_vC_trap_z.plot(t_trap * 1000, vC_trap, label=f'n={n}', alpha=0.8)

        # Plota transitório
        ax_iL_eul_trans.plot(t_eul * 1000, iL_eul, label=f'n={n}', alpha=0.8)
        ax_iL_trap_trans.plot(t_trap * 1000, iL_trap, label=f'n={n}', alpha=0.8)
        ax_vC_eul_trans.plot(t_eul * 1000, vC_eul, label=f'n={n}', alpha=0.8)
        ax_vC_trap_trans.plot(t_trap * 1000, vC_trap, label=f'n={n}', alpha=0.8)

    
    qs_style = {'color': 'black', 'linewidth': 1.1, 'linestyle': '-', 'alpha': 0.5, 'label': 'QSpice'}
    
    # Adiciona QSpice em todos os gráficos
    for ax_target in [ax_iL_eul, ax_iL_trap, ax_iL_eul_z, ax_iL_trap_z, ax_iL_eul_trans, ax_iL_trap_trans]:
        ax_target.plot(t_qs * 1000, iL_qs, **qs_style)
        
    for ax_target in [ax_vC_eul, ax_vC_trap, ax_vC_eul_z, ax_vC_trap_z, ax_vC_eul_trans, ax_vC_trap_trans]:
        ax_target.plot(t_qs * 1000, vC_qs, **qs_style)
        
    # Adiciona as legendas no canto inferior direito usando o tamanho configurado
    for ax in [ax_iL_eul, ax_iL_trap, ax_vC_eul, ax_vC_trap, 
               ax_iL_eul_z, ax_iL_trap_z, ax_vC_eul_z, ax_vC_trap_z,
               ax_iL_eul_trans, ax_iL_trap_trans, ax_vC_eul_trans, ax_vC_trap_trans]:
        ax.legend(loc='lower right', fontsize=FONT_LEGEND)
    
    # Ajusta o espaçamento interno de todas as figuras
    fig_iL.tight_layout()
    fig_vC.tight_layout()
    fig_iL_z.tight_layout()
    fig_vC_z.tight_layout()
    fig_iL_trans.tight_layout()
    fig_vC_trans.tight_layout()
    
    # Salvando as imagens
    fig_iL.savefig('corrente_completa.png', dpi=DPI)
    fig_vC.savefig('tensao_completa.png', dpi=DPI)
    fig_iL_z.savefig('corrente_permanente.png', dpi=DPI)
    fig_vC_z.savefig('tensao_permanente.png', dpi=DPI)
    fig_iL_trans.savefig('corrente_trans.png', dpi=DPI)
    fig_vC_trans.savefig('tensao_trans.png', dpi=DPI)

    plt.close('all')

if __name__ == "__main__":
    main()