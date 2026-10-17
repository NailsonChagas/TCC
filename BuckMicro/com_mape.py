import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

# ==========================================
# 1. CONFIGURAÇÕES E PARÂMETROS
# ==========================================
FONT_TITLE = 14
FONT_LABEL = 12
FONT_TICKS = 11
FONT_LEGEND = 11
DPI = 200

DAC_BITS = [8, 10, 12, 16, 18]

QSPICE_COLOR = "gray"
QSPICE_size = 1.2
QSPICE_alpha = 0.8


# Intervalos de tempo com rótulos
TIME_INTERVALS = [
    (0.0, 0.85, "Regime Transitório"),
    (2.0, 2.2, "Regime Permanente 25V"),  
    (4.95, 5.4, r"Degrau de $V_{ref}$: 25 $\rightarrow$ 35 V"),  
    (9.0, 9.2, "Regime Permanente 35V"),   
]

CSV_BASE_NAME = "simulador_controlador_"
CSV_REFERENCIA = "buck_filtro_controle.csv"

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

# Carregando a referência do QSpice
try:
    df_ref = pd.read_csv(CSV_REFERENCIA)
    df_ref['Time_ms'] = df_ref['Time'] * 1000
    
    # Criando colunas com os mesmos nomes usados para o controlador para facilitar a plotagem
    df_ref['V(il)_real'] = df_ref['I(L1)']
    df_ref['V(vc)_real'] = df_ref['V(buck)']
except FileNotFoundError:
    print(f"Aviso: Arquivo de referência {CSV_REFERENCIA} não encontrado.")
    df_ref = None

# ==========================================
# 4. IMAGEM 1: Sinais Completos Superpostos
# ==========================================
signals_img1 = [
    ("V(il)_real", r"$i_L$ [A]"),
    ("V(vc)_real", r"$v_C$ [V]"),
]

fig1, axes1 = plt.subplots(len(signals_img1), 1, figsize=(10, 7), sharex=True, dpi=DPI)

# Plotando a referência do QSpice no fundo (zorder=1, cinza um pouco mais sólido e fino)
if df_ref is not None:
    for idx, (col, ylabel) in enumerate(signals_img1):
        if col in df_ref.columns:
            axes1[idx].plot(df_ref["Time_ms"], df_ref[col], label='QSPICE (analógica)', 
                            color=QSPICE_COLOR, linestyle='-', linewidth=QSPICE_size, alpha=QSPICE_alpha, zorder=1)

# Plotando os dados do DAC por cima (zorder padrão ou maior)
for bits, df in data_dict.items():
    time = df["Time_ms"]
    for idx, (col, ylabel) in enumerate(signals_img1):
        if col in df.columns:
            axes1[idx].plot(time, df[col], label=f"{bits} bits", linewidth=1.3, zorder=5)

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
# 5. IMAGENS 2 e 3: Zoom nos Intervalos
# ==========================================
signals_to_plot = [
    ("V(il)_real", r"$i_L$ [A]", "zoom_intervalos_corrente.png"), 
    ("V(vc)_real", r"$v_C$ [V]", "zoom_intervalos_tensao.png")
]

for col_name, y_label, filename in signals_to_plot:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), dpi=DPI)
    for idx, (t_start_ms, t_end_ms, interval_label) in enumerate(TIME_INTERVALS):
        r_idx = idx // 2  
        c_idx = idx % 2   
        ax = axes[r_idx, c_idx]
        
        # Plotando a referência do QSpice no fundo
        if df_ref is not None and col_name in df_ref.columns:
            mask_ref = (df_ref["Time_ms"] >= t_start_ms) & (df_ref["Time_ms"] <= t_end_ms)
            if mask_ref.any():
                ax.plot(df_ref.loc[mask_ref, "Time_ms"], df_ref.loc[mask_ref, col_name], 
                        label='QSPICE (analógica)', color=QSPICE_COLOR, linestyle='-', linewidth=QSPICE_size, alpha=QSPICE_alpha, zorder=1)
        
        # Plotando os dados do DAC por cima
        for bits, df in data_dict.items():
            mask = (df["Time_ms"] >= t_start_ms) & (df["Time_ms"] <= t_end_ms)
            if mask.any():
                ax.plot(df.loc[mask, "Time_ms"], df.loc[mask, col_name], label=f"{bits} bits", linewidth=1.2, zorder=5)
        
        ax.set_title(interval_label, fontsize=FONT_LABEL)
        ax.tick_params(labelsize=FONT_TICKS)
        ax.grid(True, linestyle="--", alpha=0.6)
        
        if c_idx == 0:
            ax.set_ylabel(y_label, fontsize=FONT_LABEL)
        if r_idx == 1:
            ax.set_xlabel("Tempo [ms]", fontsize=FONT_LABEL)
        if idx == 0:
            ax.legend(fontsize=FONT_LEGEND - 2, loc="best", framealpha=0.9)

    plt.tight_layout()
    plt.savefig(filename, dpi=DPI)
    plt.close()

# ==========================================
# 6. CÁLCULO E PLOTAGEM DO ERRO MAPE
# ==========================================
if df_ref is not None:
    t_ref = df_ref['Time'].values
    v_ref = df_ref['V(buck)'].values
    i_ref = df_ref['I(L1)'].values

    mape_results = []

    for bits, df_test in data_dict.items():
        t_test = df_test['Time'].values
        
        # Interpola a referência contínua para a base de tempo do teste quantizado
        v_ref_interp = np.interp(t_test, t_ref, v_ref)
        i_ref_interp = np.interp(t_test, t_ref, i_ref)
        
        v_test = df_test['V(vc)_real'].values
        i_test = df_test['V(il)_real'].values
        
        # Máscaras para evitar divisão por zero (ignora cálculos quando o sinal é próximo de zero no instante inicial)
        mask_v = np.abs(v_ref_interp) > 0.1
        mask_i = np.abs(i_ref_interp) > 0.05
        
        mape_v = np.mean(np.abs((v_ref_interp[mask_v] - v_test[mask_v]) / v_ref_interp[mask_v])) * 100
        mape_i = np.mean(np.abs((i_ref_interp[mask_i] - i_test[mask_i]) / i_ref_interp[mask_i])) * 100

        mape_results.append({
            'Bits': bits,
            'Erro_vC_ZOH_percent': mape_v,
            'Erro_iL_ZOH_percent': mape_i
        })

    df_errors = pd.DataFrame(mape_results)

    # Plotando os erros MAPE
    plt.figure(figsize=(6, 5), dpi=DPI)
    
    # Eixo X representando a resolução do DAC em Bits
    eixo_x = 'Bits' 
    
    plt.plot(df_errors[eixo_x], df_errors['Erro_vC_ZOH_percent'], marker='o', label='Erro $v_C$ (%)')
    plt.plot(df_errors[eixo_x], df_errors['Erro_iL_ZOH_percent'], marker='s', label='Erro $i_L$ (%)')
    
    plt.xlabel('Resolução do DAC [bits]', fontsize=FONT_LABEL)
    plt.xticks(DAC_BITS) 
    
    plt.ylabel('Erro [%]', fontsize=FONT_LABEL)
    plt.grid(True, which="both", ls="--", alpha=0.6)
    plt.legend(fontsize=FONT_LEGEND)
    plt.tight_layout()
    plt.savefig("teste_erros_mape.png", dpi=DPI, bbox_inches='tight')
    plt.close()

    print("Cálculo do MAPE e plotagem com QSpice concluídos com sucesso.")
else:
    print("Ocorreu um erro no cálculo porque o arquivo de referência do QSpice não foi carregado.")