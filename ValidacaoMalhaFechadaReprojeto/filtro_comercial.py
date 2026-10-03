import numpy as np

# Séries comerciais E12 e E24
E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]
E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 
       3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]

def gerar_serie_comercial(base, decadas):
    """Gera valores comerciais multiplicados pelas décadas especificadas."""
    valores = []
    for d in decadas:
        for b in base:
            valores.append(b * (10 ** d))
    return np.array(valores)

# ============================================================
# PARÂMETROS ALVO DO PROJETO
# ============================================================
a0_ideal = 9.87e06
a1_ideal = 5441

# Definindo faixas de busca para componentes padrão
# Capacitores em Farads (ex: de 1 nF a 100 nF -> potências -9 a -8)
capacitores = gerar_serie_comercial(E24, range(-9, -7)) 
# Resistores em Ohms (ex: de 100 ohms a 100 kohms -> potências 2 a 5)
resistores = gerar_serie_comercial(E24, range(2, 6))     

melhores_opcoes = []

# ============================================================
# VARREDURA E TESTE DE COMBINAÇÕES
# ============================================================
print("Buscando combinações comerciais ótimas...")

for C1 in capacitores:
    for C2 in capacitores:
        # Filtra por razões próximas à ideal (~0.75) para otimizar o desempenho do Bessel
        razao = C2 / C1
        if 0.5 <= razao <= 1.2:
            for R in resistores:
                # Fórmulas Sallen-Key para R1 = R2 = R
                a0_calc = 1 / (R**2 * C1 * C2)
                a1_calc = 2 / (R * C1)
                
                # Cálculo do erro percentual combinado
                erro_a0 = abs(a0_calc - a0_ideal) / a0_ideal
                erro_a1 = abs(a1_calc - a1_ideal) / a1_ideal
                erro_total = erro_a0 + erro_a1
                
                melhores_opcoes.append({
                    'R': R,
                    'C1': C1,
                    'C2': C2,
                    'a0': a0_calc,
                    'a1': a1_calc,
                    'erro': erro_total
                })

# Ordenar do menor erro para o maior
melhores_opcoes = sorted(melhores_opcoes, key=lambda x: x['erro'])

# ============================================================
# EXIBIÇÃO DOS RESULTADOS
# ============================================================
print("\nTop 5 Melhores Combinações Comerciais (Série E24):")
print("=" * 65)
for i in range(min(5, len(melhores_opcoes))):
    opt = melhores_opcoes[i]
    r_kohm = opt['R'] / 1e3
    c1_nf = opt['C1'] * 1e9
    c2_nf = opt['C2'] * 1e9
    
    err_a0_pct = abs(opt['a0'] - a0_ideal) / a0_ideal * 100
    err_a1_pct = abs(opt['a1'] - a1_ideal) / a1_ideal * 100
    
    print(f"{i+1}. R1 = R2 = {r_kohm:.2f} kΩ | C1 = {c1_nf:.1f} nF | C2 = {c2_nf:.1f} nF")
    print(f"   -> a0 calculado: {opt['a0']:.2e} (Erro: {err_a0_pct:.2f}%)")
    print(f"   -> a1 calculado: {opt['a1']:.2e} (Erro: {err_a1_pct:.2f}%)")
    print("-" * 65)