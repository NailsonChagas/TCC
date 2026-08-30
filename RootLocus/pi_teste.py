import control as ct
import numpy as np
import matplotlib.pyplot as plt

s = ct.TransferFunction.s

# 1. Definição das Funções (Substitua pelos valores calculados do seu controlador)
G = 1.984e11 / (s**2 + 1.332e5*s + 3.968e9)
H = 9.87e8 / (s**2 + 5.441e4*s + 9.87e8)

# Exemplo com os ganhos do PI projetado anteriormente:
KP = 0.000705 # 0.000705183846243993
KI = 120.180633 # 120.18063259599076
z_pi = KI / KP
C = KP * ((s + z_pi) / s)

# 2. Fechamento da Malha T(s) = (C * G) / (1 + C * G * H)
# A função feedback(sys1, sys2) calcula sys1 / (1 + sys1 * sys2)
T = ct.feedback(C * G, H)

# 3. Simulação da Resposta ao Degrau
# O vetor de tempo força a análise nos primeiros milissegundos
time_vector = np.linspace(0, 0.002, 2000)
time, response = ct.step_response(T, T=time_vector)

# 4. Extração Automática das Métricas
info = ct.step_info(T, SettlingTimeThreshold=0.02)

overshoot = info['Overshoot']
settling_time = info['SettlingTime']
steady_state_value = response[-1]
ess = abs(1 - steady_state_value) * 100  # Erro percentual

# 5. Verificação e Impressão dos Resultados
print("--- VERIFICAÇÃO DOS REQUISITOS ---")
print(f"Sobressinal (Mp): {overshoot:.2f}% (Requisito: <= 5%) -> {'OK' if overshoot <= 5 else 'FALHOU'}")
print(f"Tempo de Assent. (ts): {settling_time*1000:.3f} ms (Requisito: <= 0.5 ms) -> {'OK' if settling_time <= 0.0005 else 'FALHOU'}")
print(f"Erro de Regime (ess): {ess:.2f}% (Requisito: <= 1%) -> {'OK' if ess <= 1 else 'FALHOU'}")

# 6. Validação Gráfica
plt.figure(figsize=(10, 6))
plt.plot(time * 1000, response, label='Resposta ao Degrau (Malha Fechada)', linewidth=2)
plt.axhline(y=1.05, color='r', linestyle=':', label='Limite de Sobressinal (5%)')
plt.axhline(y=1.02, color='g', linestyle='--', label='Banda de 2% (Superior)')
plt.axhline(y=0.98, color='g', linestyle='--', label='Banda de 2% (Inferior)')
plt.axvline(x=0.5, color='purple', linestyle='-.', label='Limite de Tempo (0.5 ms)')
plt.xlabel('Tempo (ms)')
plt.ylabel('Amplitude')
plt.grid(True)
plt.legend()
plt.savefig('validacao_requisitos.png', dpi=400, bbox_inches='tight')
plt.show()