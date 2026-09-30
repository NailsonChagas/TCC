from controllers.AppController import AppController
from views.MainWindow import MainWindow
from models.BuckConverterCCM import BuckConverterCCM, CCMError

if __name__ == "__main__":

    # controller = AppController()
    # app = MainWindow(controller=controller)
    # app.mainloop()


    print("-" * 50)
    print("1. PROJETO TEÓRICO (A partir das especificações)")
    print("-" * 50)
    buck_teorico = BuckConverterCCM.from_design_parameters(
        Vs=50.0, 
        Vo=25.0, 
        Po=15.0, 
        delta_iL=0.1, 
        delta_Vo=0.15, 
        fs=10000.0
    )
    print(buck_teorico)
    print(f"Indutância Crítica (Lmin): {buck_teorico.Lmin:.6e} H")
    
    print("\n" + "-" * 50)
    print("2. ANÁLISE REAL (Com os componentes comerciais adotados)")
    print("-" * 50)
    buck_real = BuckConverterCCM.from_circuit_components(
        Vs=50.0, Vo=25.0, R=41.666666666666664, L=0.0125, C=8.333333333333334e-06, fs=10000.0
    )
    print(buck_real)
    print(f"Potência Real de Saída (Po): {buck_real.Po:.4f} W")
    print(f"Corrente Média Indutor (iL): {buck_real.iL:.4f} A")
    print(f"Indutância Crítica (Lmin):   {buck_real.Lmin:.6e} H")
    print(f"Ondulação de Corrente (A):   {buck_real.delta_iL*100:.4f}%")
    print(f"Ondulação de Tensão (V):     {buck_real.delta_Vo*100:.4f}%")