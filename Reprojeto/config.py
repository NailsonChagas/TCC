import numpy as np

# Configurações de Gráficos
FONT_TITLE = 16    
FONT_LABEL = 13    
FONT_TICKS = 12    
FONT_LEGEND = 13 
DPI = 200    

# Parâmetros da Simulação
MAX_SIM_TIME = 80e-3 # Segundos (6 ms)
FS = 5000
TIME_STEP = 1 / FS

TIME_INTERVALS_ZOH = [
    (0.0, 20, "Regime Transitório"),
    (32, 34, "Regime Permanente"),  
    (0.0, 80, "Visão Geral")  
]

F_MULTIPLIERS = [1, 10, 100, 1000, 10000]
TICKS_TO_SHOW = [1, 10, 100, 1000, 10000]