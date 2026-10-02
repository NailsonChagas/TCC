from BuckConverterCCM import BuckConverterCCM
from config import *

# y[k] = 0.060077 * x[k] + 0.120153 * x[k-1] + 0.060077 * x[k-2] - (-1.097254) * y[k-1] - (0.337560) * y[k-2] ->  filtro antialising discretizado com 2khz
# u[k] = 0.000048 * e[k] + 0.000034 * e[k-1] - (-1.000000) * u[k-1]

if __name__ == "__main__": 
    print("-" * 50)
    print("1. PROJETO TEÓRICO (A partir das especificações)")
    print("-" * 50)
    buck_teorico = BuckConverterCCM.from_design_parameters(
        Vs=50.0, 
        Vo=25.0, 
        Po=15.0, 
        delta_iL=0.3, 
        delta_Vo=0.15, 
    )
    print(buck_teorico)
    print(f"Indutância Crítica (Lmin): {buck_teorico.Lmin:.6e} H")

    print("\n" + "-" * 50)
    print("2. ANÁLISE REAL (Com os componentes comerciais adotados)")
    print("-" * 50)
    buck_real = BuckConverterCCM.from_circuit_components(
        Vs=50.0, Vo=25.0, R=41.7, L=0.0083, C=5e-05, fs=5000
    )
    print(buck_real)
    print(f"Potência Real de Saída (Po): {buck_real.Po:.4f} W")
    print(f"Corrente Média Indutor (iL): {buck_real.iL:.4f} A")
    print(f"Indutância Crítica (Lmin):   {buck_real.Lmin:.6e} H")
    print(f"Ondulação de Corrente (A):   {buck_real.delta_iL*100:.4f}%")
    print(f"Ondulação de Tensão (V):     {buck_real.delta_Vo*100:.4f}%")

    print("\n" + "-" * 50)
    print("3. PROJETO DO FILTRO ANTIALIASING (TUSTIN)")
    print("-" * 50)
    buck_real.design_and_discretize_antialiasing_tustin()

    print("\n" + "-" * 50)
    print("4. COMPARAÇÃO ZOH vs QSPICE (Malha Aberta)")
    print("-" * 50)
    
    filepath_qspice = "BuckCCM2k.csv"

    try:
        buck_real.plot_comparison(filepath_qspice, F_MULTIPLIERS)
    except FileNotFoundError:
        print(f"ERRO: O arquivo '{filepath_qspice}' não foi encontrado.")
        print("Por favor, coloque o arquivo CSV do QSPICE no mesmo diretório ou atualize o caminho.")