import pandas as pd
import matplotlib.pyplot as plt

# Configurações dos gráficos
FONT_TITLE = 14
FONT_LABEL = 12
FONT_TICKS = 10
FONT_LEGEND = 11
DPI = 200  # Ajustado para evitar estouro de escala em alguns visores

# 1. Carregar os dados do arquivo CSV
df = pd.read_csv('buck.csv')

# Converter o tempo de segundos para milissegundos (ms)
time_ms = df['Time'] * 1000

# 2. Criar a figura com 1 linha e 2 colunas
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 8), dpi=DPI)

# 3. Configurar o primeiro gráfico: Corrente I(L1)
ax1.plot(time_ms, df['I(L1)'], color='tab:blue', linewidth=1.2, label=r'$i_L$')
ax1.set_xlabel('Tempo (ms)', fontsize=FONT_LABEL)
ax1.set_ylabel(r'$i_L$ (A)', fontsize=FONT_LABEL)
ax1.tick_params(axis='both', labelsize=FONT_TICKS)
ax1.legend(fontsize=FONT_LEGEND, loc='best')
ax1.grid(True, linestyle='--', alpha=0.6)

# 4. Configurar o segundo gráfico: Tensão V(n02)
ax2.plot(time_ms, df['V(n02)'], color='tab:orange', linewidth=1.2, label=r'$v_C$')
ax2.set_xlabel('Tempo (ms)', fontsize=FONT_LABEL)
ax2.set_ylabel(r'$v_C$ (V)', fontsize=FONT_LABEL)
ax2.tick_params(axis='both', labelsize=FONT_TICKS)
ax2.legend(fontsize=FONT_LEGEND, loc='best')
ax2.grid(True, linestyle='--', alpha=0.6)

# 5. Ajustar o espaçamento e salvar a imagem
plt.tight_layout()
plt.savefig('buck_plot_i_v.png', dpi=DPI)

# 6. Exibir o gráfico na tela
plt.show()