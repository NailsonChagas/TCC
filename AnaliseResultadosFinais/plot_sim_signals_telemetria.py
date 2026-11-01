import pandas as pd
import matplotlib.pyplot as plt

# ==========================================
# CONSTANTES DE FORMATAÇÃO
# ==========================================
FONT_TITLE = 16    
FONT_LABEL = 13    
FONT_TICKS = 12    
FONT_LEGEND = 13 
DPI = 200    

def plot_csv_signals(filepath='resultado_malha_fechada2.csv', t_ligado=1073.4520, t_degrau=30268.9620):
    # Carregar os dados do ficheiro
    df = pd.read_csv(filepath)
    
    # Limpar possíveis espaços nos nomes das colunas
    df.columns = [c.strip() for c in df.columns]
    
    # ==========================================
    # CORREÇÃO: Ordenar os dados cronologicamente
    # ==========================================
    df = df.sort_values(by='Tempo [ms]').reset_index(drop=True)
    
    # Extrair vetores
    t_ms = df['Tempo [ms]'].values
    vC = df['vC [V]'].values
    iL = df['iL [A]'].values
    
    # Tempo máximo da simulação para a Visão Geral
    t_max = t_ms.max()

    figsize_aux = (10, 10)
    
    # ==========================================
    # DEFINIÇÃO DINÂMICA DAS JANELAS E TÍTULOS
    # ==========================================
    # Ajusta as janelas colocando uma margem antes e depois do evento
    windows = [
        (t_ligado - 20, t_ligado + 80),                # Janela de 100ms em torno do controlador ligado
        (t_ligado + 80, t_ligado + (80*2)),   
        (t_degrau - 50, t_degrau + 150),               # Janela de 200ms em torno do degrau
        (0, t_max)                                     # Visão Geral dinâmica
    ]
    
    window_titles = [
        f'Ativação do Controlador', 
        f'Regime Permanente', 
        rf'Degrau de $V_{{ref}}$', 
        f'Visão Geral'
    ]
    
    # Criação das figuras
    fig_vC, axes_vC = plt.subplots(nrows=2, ncols=2, figsize=figsize_aux)
    fig_iL, axes_iL = plt.subplots(nrows=2, ncols=2, figsize=figsize_aux)
    
    axes_vC_flat = axes_vC.flatten()
    axes_iL_flat = axes_iL.flatten()
    
    for j, window in enumerate(windows):
        row, col = divmod(j, 2) 
        
        # Gráficos de Tensão (vC)
        ax_vC = axes_vC_flat[j]
        ax_vC.plot(t_ms, vC, label='vC (Telemetria)', color='tab:blue')
        ax_vC.set_xlim(window)
        ax_vC.grid(True, alpha=0.5, linestyle='--')
        ax_vC.set_title(window_titles[j], fontsize=FONT_TITLE)
        
        if row == 1: ax_vC.set_xlabel('Tempo (ms)', fontsize=FONT_LABEL)
        if col == 0: ax_vC.set_ylabel('Tensão (V)', fontsize=FONT_LABEL)
        if j == 3: ax_vC.legend(loc='lower right', fontsize=FONT_LEGEND)

        # Gráficos de Corrente (iL)
        ax_iL = axes_iL_flat[j]
        ax_iL.plot(t_ms, iL, label='iL (Telemetria)', color='tab:red')
        ax_iL.set_xlim(window)
        ax_iL.grid(True, alpha=0.5, linestyle='--')
        ax_iL.set_title(window_titles[j], fontsize=FONT_TITLE)
        
        if row == 1: ax_iL.set_xlabel('Tempo (ms)', fontsize=FONT_LABEL)
        if col == 0: ax_iL.set_ylabel('Corrente (A)', fontsize=FONT_LABEL)
        if j == 3: ax_iL.legend(loc='lower right', fontsize=FONT_LEGEND)

    fig_vC.tight_layout()
    fig_iL.tight_layout()
    
    # Guardar as imagens
    fig_vC.savefig("grafico_Telemetria_vC.png", dpi=DPI, bbox_inches='tight')
    fig_iL.savefig("grafico_Telemetria_iL.png", dpi=DPI, bbox_inches='tight')
    plt.close('all')
    print("Gráficos gerados e guardados: 'grafico_Telemetria_vC.png' e 'grafico_Telemetria_iL.png'")

# ==========================================
# EXECUÇÃO DO SCRIPT
# ==========================================
if __name__ == "__main__":
    # Basta alterar os parâmetros aqui para adaptar a novos testes
    plot_csv_signals(
        filepath='resultado_malha_fechada2.csv',
        t_ligado=1073.4520,
        t_degrau=30268.9620
    )