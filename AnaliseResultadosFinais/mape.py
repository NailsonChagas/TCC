import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

# 1. Carregar os arquivos CSV
# Certifique-se de que os arquivos estão no mesmo diretório do script ou insira o caminho completo
df_sim = pd.read_csv('sinais_simulados_n100.csv')
df_exp = pd.read_csv('resultado_malha_fechada2.csv')

# 2. Extrair os vetores
# Multiplicando 'Time' por 1000 assumindo que a simulação exportou o tempo em segundos
t_sim = df_sim['Time'].values * 1000  
vC_sim = df_sim['vC'].values
iL_sim = df_sim['iL'].values

# Extraindo os dados do CSV de telemetria
t_exp = df_exp['Tempo [ms]'].values
vC_exp = df_exp['vC [V]'].values
iL_exp = df_exp['iL [A]'].values

# 3. Interpolar os sinais simulados para os mesmos instantes de tempo da telemetria
vC_sim_interp = np.interp(t_exp, t_sim, vC_sim)
iL_sim_interp = np.interp(t_exp, t_sim, iL_sim)

# 4. Função para calcular o MAPE ignorando a região onde o sinal é zero
def calculate_mape_masked(y_true, y_pred, threshold=0.5):
    # Cria uma máscara para considerar apenas instantes onde o sinal de referência é maior que o limiar
    mask = y_true > threshold 
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

# 5. Calcular os erros
# MAPE (%) - Ignorando a parte em que os conversores ainda não partiram
mape_vC = calculate_mape_masked(vC_sim_interp, vC_exp, threshold=0.1) # Ignora valores abaixo de 1V
mape_iL = calculate_mape_masked(iL_sim_interp, iL_exp, threshold=0.1) # Ignora valores abaixo de 0.1A

# MAE (Erro Absoluto Médio - em Volts e Amperes)
mae_vC = mean_absolute_error(vC_sim_interp, vC_exp)
mae_iL = mean_absolute_error(iL_sim_interp, iL_exp)

# RMSE (Raiz do Erro Quadrático Médio - em Volts e Amperes)
rmse_vC = np.sqrt(mean_squared_error(vC_sim_interp, vC_exp))
rmse_iL = np.sqrt(mean_squared_error(iL_sim_interp, iL_exp))

# 6. Exibir os resultados
print("--- TENSÃO vC ---")
print(f"MAPE: {mape_vC:.2f}% (considerando apenas a região ativa)")
print(f"MAE:  {mae_vC:.4f} V")
print(f"RMSE: {rmse_vC:.4f} V\n")

print("--- CORRENTE iL ---")
print(f"MAPE: {mape_iL:.2f}% (considerando apenas a região ativa)")
print(f"MAE:  {mae_iL:.4f} A")
print(f"RMSE: {rmse_iL:.4f} A")