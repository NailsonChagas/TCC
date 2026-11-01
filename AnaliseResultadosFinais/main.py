import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. Carregar os dados
df = pd.read_csv('resultado_malha_fechada2.csv')
df.columns = [c.strip() for c in df.columns]

tempo = df['Tempo [ms]'].values
iL = df['iL [A]'].values
vC = df['vC [V]'].values

# =============================================================================
# Identificação: Tempo de Ligamento (t_ligado)
# =============================================================================
# Deteta o momento exato em que a corrente no indutor (iL) sai de zero.
limiar_iL_ligado = 0.05 
idx_ligado = np.argmax(iL > limiar_iL_ligado)
t_ligado = tempo[idx_ligado]

# =============================================================================
# Identificação: Tempo do Degrau na Referência (t_degrau)
# =============================================================================
# Passo A: Filtrar o ripple com uma janela de média móvel
vC_suave = pd.Series(vC).rolling(window=100, min_periods=1).mean().values

# Passo B: Garantir que procuramos o degrau apenas após o transiente de arranque
mascara_pos_arranque = tempo > (t_ligado + 5)

# Passo C: Encontrar um ponto a meio da rampa do degrau (ex: 32V)
idx_meio_degrau = np.argmax((vC_suave > 32.0) & mascara_pos_arranque)

# Passo D: Busca reversa a partir da rampa até à quebra do regime anterior.
# O limiar de 27.0V garante que a busca para no início da rampa do degrau,
# evitando recuar pelo regime permanente que estabilizou perto dos 26V.
idx_inicio_degrau = idx_meio_degrau
while idx_inicio_degrau > 0 and vC_suave[idx_inicio_degrau] > 27.0:
    idx_inicio_degrau -= 1

t_degrau = tempo[idx_inicio_degrau]

# =============================================================================
# Resultados e Visualização
# =============================================================================
print(f"Momento em que o controlador foi LIGADO: {t_ligado:.4f} ms")
print(f"Momento do DEGRAU na referência: {t_degrau:.4f} ms")

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

# Gráfico da Corrente (iL)
ax1.plot(tempo, iL, color='orange', alpha=0.7, label='iL [A]')
ax1.axvline(x=t_ligado, color='green', linestyle='--', label=f'Ligado: {t_ligado:.4f} ms')
ax1.axvline(x=t_degrau, color='red', linestyle='--', label=f'Degrau: {t_degrau:.4f} ms')
ax1.set_ylabel('Corrente [A]')
ax1.set_title('Dinâmica do Indutor e Tensão no Condensador')
ax1.legend()
ax1.grid(True)

# Gráfico da Tensão (vC)
ax2.plot(tempo, vC, color='gray', alpha=0.4, label='vC [V] (Original)')
ax2.plot(tempo, vC_suave, color='blue', label='vC [V] (Média Móvel)')
ax2.axvline(x=t_ligado, color='green', linestyle='--')
ax2.axvline(x=t_degrau, color='red', linestyle='--')
ax2.plot(t_degrau, vC_suave[idx_inicio_degrau], 'ro')
ax2.set_xlabel('Tempo [ms]')
ax2.set_ylabel('Tensão [V]')
ax2.legend()
ax2.grid(True)

plt.tight_layout()
plt.show()