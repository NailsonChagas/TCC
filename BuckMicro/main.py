import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. CONFIGURAÇÕES E PARÂMETROS
# ==========================================
FONT_TITLE = 14
FONT_LABEL = 12
FONT_TICKS = 11
FONT_LEGEND = 11
DPI = 200

DAC_BITS = [8, 10, 12, 16, 18]

# Intervalos de tempo com rótulos
TIME_INTERVALS = [
    (0.0, 0.85, "Regime Transitório"),
    (2.0, 2.2, "Regime Permanente 25V"),  
    (4.95, 5.4, r"Degrau de $V_{ref}$: 25 $\rightarrow$ 35 V"),  
    (9.0, 9.2, "Regime Permanente 35V"),   
]

CSV_BASE_NAME = "simulador_controlador_"

# ==========================================
# 2. CONSTANTES DE CONVERSÃO
# ==========================================
VDAC_MAX = 3.3   # Tensão máxima do DAC [V]
VC_MAX = 50.0    # Faixa máxima de tensão da planta [V]
IL_MAX = 5.0     # Faixa máxima de corrente da planta [A]

# ==========================================
# 3. CARREGAMENTO E CONVERSÃO DOS DADOS
# ==========================================
data_dict = {}
for bits in DAC_BITS:
    filename = f"{CSV_BASE_NAME}{bits}.csv"
    try:
        df = pd.read_csv(filename)
        
        # Converte os valores do DAC para as grandezas reais da planta
        df['V(il)_real'] = df['V(il)'] * IL_MAX / VDAC_MAX
        df['V(vc)_real'] = df['V(vc)'] * VC_MAX / VDAC_MAX
        
        if 'V(filtro)' in df.columns:
            df['V(filtro)_real'] = df['V(filtro)'] * VC_MAX / VDAC_MAX

        # Converter tempo de segundos para milissegundos
        df['Time_ms'] = df['Time'] * 1000
        
        data_dict[bits] = df
    except FileNotFoundError:
        print(f"Aviso: Arquivo {filename} não encontrado. Certifique-se de que ele está na pasta.")

# ==========================================
# 4. IMAGEM 1: Sinais Completos Superpostos
# ==========================================
signals_img1 = [
    ("V(il)_real", r"$i_L$ [A]"),
    ("V(vc)_real", r"$v_C$ [V]"),
]

fig1, axes1 = plt.subplots(len(signals_img1), 1, figsize=(10, 7), sharex=True, dpi=DPI)

for bits, df in data_dict.items():
    time = df["Time_ms"]
    for idx, (col, ylabel) in enumerate(signals_img1):
        if col in df.columns:
            axes1[idx].plot(time, df[col], label=f"{bits} bits", linewidth=1.2)

for idx, (col, ylabel) in enumerate(signals_img1):
    axes1[idx].set_ylabel(ylabel, fontsize=FONT_LABEL)
    axes1[idx].tick_params(labelsize=FONT_TICKS)
    axes1[idx].grid(True, linestyle="--", alpha=0.6)
    if idx == 0:
        axes1[idx].legend(loc="upper right", fontsize=FONT_LEGEND, framealpha=0.9)

axes1[-1].set_xlabel("Tempo [ms]", fontsize=FONT_LABEL)
plt.tight_layout()
plt.savefig("sinais_completos_dac.png", dpi=DPI)
plt.close()

# ==========================================
# 5. IMAGENS 2 e 3: Zoom nos Intervalos (2x2 para Corrente, 2x2 para Tensão)
# ==========================================
signals_to_plot = [
    ("V(il)_real", r"$i_L$ [A]", "zoom_intervalos_corrente.png"), 
    ("V(vc)_real", r"$v_C$ [V]", "zoom_intervalos_tensao.png")
]

# Itera sobre os sinais (primeiro corrente, depois tensão)
for col_name, y_label, filename in signals_to_plot:
    
    # Cria uma figura 2x2 para o sinal atual
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), dpi=DPI)
    
    # Itera sobre os 4 intervalos temporais para distribuí-los na grade 2x2
    for idx, (t_start_ms, t_end_ms, interval_label) in enumerate(TIME_INTERVALS):
        
        # Calcula a posição na matriz 2x2
        r_idx = idx // 2  # Linha: 0 para idx 0,1 | 1 para idx 2,3
        c_idx = idx % 2   # Coluna: 0 para idx 0,2 | 1 para idx 1,3
        ax = axes[r_idx, c_idx]
        
        # Plota os dados de cada resolução de DAC
        for bits, df in data_dict.items():
            mask = (df["Time_ms"] >= t_start_ms) & (df["Time_ms"] <= t_end_ms)
            
            if mask.any():
                ax.plot(df.loc[mask, "Time_ms"], df.loc[mask, col_name], label=f"{bits} bits", linewidth=1.2)
        
        # Formatação do Subplot
        ax.set_title(interval_label, fontsize=FONT_LABEL)
        ax.tick_params(labelsize=FONT_TICKS)
        ax.grid(True, linestyle="--", alpha=0.6)
        
        # Adiciona rótulo no eixo Y apenas na primeira coluna (c_idx == 0)
        if c_idx == 0:
            ax.set_ylabel(y_label, fontsize=FONT_LABEL)
            
        # Adiciona rótulo no eixo X apenas na última linha (r_idx == 1)
        if r_idx == 1:
            ax.set_xlabel("Tempo [ms]", fontsize=FONT_LABEL)
            
        # Adiciona a legenda apenas no primeiro gráfico para evitar poluição
        if idx == 0:
            ax.legend(fontsize=FONT_LEGEND - 2, loc="best", framealpha=0.9)

    plt.tight_layout()
    plt.savefig(filename, dpi=DPI)
    plt.close()