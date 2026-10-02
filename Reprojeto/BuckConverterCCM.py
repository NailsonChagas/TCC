import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
from scipy.linalg import expm
from scipy import signal
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from config import FS, MAX_SIM_TIME, TIME_STEP, TIME_INTERVALS_ZOH, TICKS_TO_SHOW
from config import FONT_TITLE, FONT_LABEL, FONT_TICKS, FONT_LEGEND, DPI

def calc_mape(y_true, y_pred, threshold=0.05):
    """Calcula o Erro Percentual Absoluto Médio (MAPE)."""
    mask = np.abs(y_true) > threshold
    if np.sum(mask) == 0:
        return 0.0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

class CCMError(ValueError):
    """Exceção lançada quando o conversor não opera em CCM."""

class BuckConverterCCM:
    """
    Representação de um conversor Buck operando em Modo de Condução Contínua (CCM).
    """
    def __init__(
        self,
        Vs: float,
        Vo: float,
        R: float,
        L: float,
        C: float,
        fs: float = FS,
    ) -> None:
        self.Vs = Vs
        self.Vo = Vo
        self.R = R
        self.L = L
        self.C = C
        self.fs = fs

        if self.L <= self.Lmin:
            raise CCMError(
                f"O conversor não opera em CCM "
                f"(L={self.L:.6e} H <= Lmin={self.Lmin:.6e} H)."
            )

    @classmethod
    def from_design_parameters(
        cls,
        Vs: float,
        Vo: float,
        Po: float,
        delta_iL: float,
        delta_Vo: float,
        fs: float = FS,
    ) -> "BuckConverterCCM":
        R = Vo**2 / Po
        D = Vo / Vs

        L = Vo * (1 - D) / (delta_iL * fs)
        C = Vo * (1 - D) / (8 * L * delta_Vo * fs**2)

        return cls(Vs, Vo, R, L, C, fs)

    @classmethod
    def from_circuit_components(
        cls,
        Vs: float,
        Vo: float,
        R: float,
        L: float,
        C: float,
        fs: float = FS,
    ) -> "BuckConverterCCM":
        return cls(Vs, Vo, R, L, C, fs)

    @property
    def D(self) -> float:
        return self.Vo / self.Vs

    @property
    def Po(self) -> float:
        return self.Vo**2 / self.R

    @property
    def iL(self) -> float:
        return self.Vo / self.R

    @property
    def Lmin(self) -> float:
        return (1 - self.D) * self.R / (2 * self.fs)

    @property
    def delta_iL(self) -> float:
        return self.Vo * (1 - self.D) / (self.L * self.fs)

    @property
    def delta_Vo(self) -> float:
        return (
            self.Vo
            * (1 - self.D)
            / (8 * self.L * self.C * self.fs**2)
        )

    def __repr__(self) -> str:
        return (
            "BuckConverterCCM("
            f"Vs={self.Vs}, "
            f"Vo={self.Vo}, "
            f"R={self.R}, "
            f"L={self.L}, "
            f"C={self.C}, "
            f"fs={self.fs}"
            ")"
        )

    def load_qspice_data(self, filepath):
        """Lê os dados brutos do QSPICE sem reamostragem, preservando o ripple original."""
        df = pd.read_csv(filepath)
        t_qspice = df['Time'].values
        vC_qspice_data = df['V(buck)'].values
        iL_qspice_data = df['I(L1)'].values
        return t_qspice, vC_qspice_data, iL_qspice_data

    def load_and_interpolate_data(self, filepath):
        """Retorna funções de interpolação apenas para o cálculo do MAPE."""
        df = pd.read_csv(filepath)
        t_qspice = df['Time'].values
        vC_qspice_data = df['V(buck)'].values
        iL_qspice_data = df['I(L1)'].values
        
        interp_vC = interp1d(t_qspice, vC_qspice_data, fill_value="extrapolate")
        interp_iL = interp1d(t_qspice, iL_qspice_data, fill_value="extrapolate")
        
        return interp_vC, interp_iL

    def simulate_buck_zoh(self, n, interp_vC, interp_iL, base_time_step=TIME_STEP):
        """Roda a simulação ZOH em malha aberta com duty cycle fixo."""
        print(f"simulate_buck_zoh(n = {n}, ...)")
        timestep = base_time_step / n
        n_points = int(MAX_SIM_TIME / timestep)
        t_sim = np.arange(n_points) * timestep

        # Matrizes de Espaço de Estados (ZOH) da planta
        A = np.array([[0, -1/self.L], [1/self.C, -1/(self.R*self.C)]])
        B1 = np.array([[1/self.L], [0]]) 
        B2 = np.array([[0], [0]]) 
        Ad = expm(A * timestep)
        A_inv = np.linalg.inv(A)
        Bd1 = A_inv @ (Ad - np.eye(2)) @ B1 
        Bd2 = A_inv @ (Ad - np.eye(2)) @ B2 

        vC_qspice_interp = interp_vC(t_sim)
        iL_qspice_interp = interp_iL(t_sim)

        iL = np.zeros(n_points)
        vC = np.zeros(n_points)

        D_fixed = self.D
        steps_per_Ts = int(np.round(1.0 / (self.fs * timestep)))

        for k in range(n_points - 1):
            is_sw_closed = (k % max(1, steps_per_Ts)) < (D_fixed * steps_per_Ts)

            if is_sw_closed:
                iL[k+1] = Ad[0,0]*iL[k] + Ad[0,1]*vC[k] + Bd1[0][0]*self.Vs
                vC[k+1] = Ad[1,0]*iL[k] + Ad[1,1]*vC[k] + Bd1[1][0]*self.Vs
            else:
                iL[k+1] = Ad[0,0]*iL[k] + Ad[0,1]*vC[k] + Bd2[0][0]*self.Vs
                vC[k+1] = Ad[1,0]*iL[k] + Ad[1,1]*vC[k] + Bd2[1][0]*self.Vs

        mape_vC = calc_mape(vC, vC_qspice_interp, threshold=0.05)
        mape_iL = calc_mape(iL, iL_qspice_interp, threshold=0.05)

        return t_sim, vC, iL, mape_vC, mape_iL

    def plot_comparison(self, filepath, n_values, base_time_step=TIME_STEP):
        """Realiza as simulações ZOH em malha aberta e plota o QSPICE comparado com o ZOH."""
        t_qspice, vC_qspice_raw, iL_qspice_raw = self.load_qspice_data(filepath)
        t_qspice_ms = t_qspice * 1000

        interp_vC, interp_iL = self.load_and_interpolate_data(filepath)
        
        sim_results = {}
        for n in n_values:
            t_sim, vC, iL, mape_vC, mape_iL = self.simulate_buck_zoh(n, interp_vC, interp_iL, base_time_step)
            sim_results[n] = {
                't_sim': t_sim, 'vC': vC, 'iL': iL, 
                'mape_vC': mape_vC, 'mape_iL': mape_iL
            }

        plt.style.use('default')
        cmap = plt.get_cmap('tab10')
        colors = [cmap(i / max(1, len(n_values) - 1)) for i in range(len(n_values))]

        num_intervals = len(TIME_INTERVALS_ZOH)
        fig_intervals, axs_int = plt.subplots(2, num_intervals, figsize=(6 * num_intervals, 8), dpi=DPI)

        for i, (t_start, t_end, title) in enumerate(TIME_INTERVALS_ZOH):
            axs_int[0, i].plot(t_qspice_ms, vC_qspice_raw, label='QSPICE', color='black', linewidth=1.5, linestyle='--')
            axs_int[1, i].plot(t_qspice_ms, iL_qspice_raw, label='QSPICE', color='black', linewidth=1.5, linestyle='--')
            
            for idx, n in enumerate(n_values):
                color = colors[idx]
                res = sim_results[n]
                t_ms = res['t_sim'] * 1000
                
                axs_int[0, i].plot(t_ms, res['vC'], label=f'n={n}', color=color, alpha=0.8)
                axs_int[1, i].plot(t_ms, res['iL'], label=f'n={n}', color=color, alpha=0.8)

            axs_int[0, i].set_xlim(t_start, t_end)
            axs_int[0, i].set_title(title, fontsize=FONT_TITLE)
            axs_int[0, i].grid(True, linestyle='--', alpha=0.6)
            axs_int[0, i].tick_params(axis='both', labelsize=FONT_TICKS)
            if i == 0:
                axs_int[0, i].set_ylabel('Tensão (V)', fontsize=FONT_LABEL)
                axs_int[0, i].legend(fontsize=FONT_LEGEND)
            
            axs_int[1, i].set_xlim(t_start, t_end)
            axs_int[1, i].set_xlabel('Tempo (ms)', fontsize=FONT_LABEL)
            axs_int[1, i].grid(True, linestyle='--', alpha=0.6)
            axs_int[1, i].tick_params(axis='both', labelsize=FONT_TICKS)
            if i == 0:
                axs_int[1, i].set_ylabel('Corrente (A)', fontsize=FONT_LABEL)
                axs_int[1, i].legend(fontsize=FONT_LEGEND)

        fig_intervals.tight_layout()
        output_intervals = "comparacao_zoh_intervalos.png"
        fig_intervals.savefig(output_intervals)
        print(f"Gráfico de intervalos salvo em: {output_intervals}")
        plt.close(fig_intervals)

        # Gráfico MAPE
        n_list = list(n_values)
        mape_vC_list = [sim_results[n]['mape_vC'] for n in n_list]
        mape_iL_list = [sim_results[n]['mape_iL'] for n in n_list]

        fig_mape, ax_mape = plt.subplots(figsize=(8, 5), dpi=DPI)
        ax_mape.plot(n_list, mape_vC_list, marker='o', linestyle='-', linewidth=2, label='MAPE Tensão (vC)')
        ax_mape.plot(n_list, mape_iL_list, marker='s', linestyle='-', linewidth=2, label='MAPE Corrente (iL)')
        
        ax_mape.set_xscale('log')
        ax_mape.set_xticks(TICKS_TO_SHOW)
        
        formatter = ScalarFormatter()
        formatter.set_scientific(False)
        ax_mape.xaxis.set_major_formatter(formatter)

        ax_mape.set_xlabel('Fator n (Resolução)', fontsize=FONT_LABEL)
        ax_mape.set_ylabel('Erro (%)', fontsize=FONT_LABEL)
        ax_mape.grid(True, which="both", linestyle='--', alpha=0.6)
        ax_mape.tick_params(axis='both', labelsize=FONT_TICKS)
        ax_mape.legend(fontsize=FONT_LEGEND)

        fig_mape.tight_layout()
        output_mape = "comparacao_mape_vs_n.png"
        fig_mape.savefig(output_mape)
        print(f"Gráfico de progressão do MAPE salvo em: {output_mape}")
        plt.close(fig_mape)

    def design_and_discretize_antialiasing_tustin(self):
        """Projeta o filtro antialiasing Bessel via Sallen-Key usando a função analítica, discretiza via Tustin e plota apenas o contínuo com linha em -40dB."""
        
        fs_sw = self.fs
        fc = fs_sw / 10.0
        
        print(f"--- PROJETO DO FILTRO ANTIALIASING (TUSTIN) ---")
        print(f"Frequência de Chaveamento (Fsw): {fs_sw / 1e3:.1f} kHz")
        print(f"Frequência de Corte (Fc): {fc / 1e3:.1f} kHz\n")
        
        # Coeficientes da função de transferência contínua fornecida:
        # H(s) = (4 * fc^2 * pi^2) / (4 * pi^2 * fc^2 + 2 * sqrt(3) * pi * fc * s + s^2)
        a0 = 4.0 * (np.pi**2) * (fc**2)
        a1 = 2.0 * np.sqrt(3) * np.pi * fc
        b0 = a0  # Ganho DC unitário
        
        b = [b0]
        a = [1.0, a1, a0]
        
        razao_c = (a1**2) / (4.0 * a0)
        c1_val = 20e-9  
        c2_calc = c1_val * razao_c
        
        multiplicadores_e12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]
        decades = [1e-9, 10e-9, 100e-9, 1e-6]
        capacitores_comerciais = [m * d for d in decades for m in multiplicadores_e12]
        
        c2_val = min(capacitores_comerciais, key=lambda x: abs(x - c2_calc))
        r_val = 2.0 / (a1 * c1_val)
        
        print(f"Componentes Calculados / Comerciais:")
        print(f"  - R1 = R2 = {r_val:.2f} Ohms (~{r_val/1e3:.2f} kOhms)")
        print(f"  - C1 = {c1_val * 1e9:.1f} nF")
        print(f"  - C2 = {c2_val * 1e9:.1f} nF (Teórico ideal: {c2_calc * 1e9:.2f} nF)\n")
        
        # Exibe a Função de Transferência Contínua H(s)
        print("--- FUNÇÃO DE TRANSFERÊNCIA CONTÍNUA H(s) ---")
        print(f"H(s) = ({b0:.8f}) / (1.0*s^2 + {a1:.8f}*s + {a0:.8f})\n")
        
        # Sistema Contínuo
        sys_cont = signal.TransferFunction(b, a)
        w, mag, phase = signal.bode(sys_cont, w=np.logspace(3, 7, 2000))
        freq_hz = w / (2 * np.pi)
        
        # Discretização Tustin
        ts = 1.0 / fs_sw
        sys_disc = signal.cont2discrete((b, a), ts, method='bilinear')
        
        num_z = np.squeeze(sys_disc[0])
        den_z = np.squeeze(sys_disc[1])
        
        b_coefs = num_z / den_z[0]
        a_coefs = den_z / den_z[0]
        
        # Plot Apenas do Filtro Contínuo com linha em -40dB
        plt.figure(figsize=(9, 7), dpi=DPI)
        
        plt.subplot(2, 1, 1)
        plt.semilogx(freq_hz, mag, color='b', linewidth=2)
        plt.axvline(fc, color='darkorange', linestyle='--', linewidth=1.5, label=f'Fc = {fc/1e3:.1f} kHz')
        plt.axvline(fs_sw, color='red', linestyle=':', linewidth=1.5, label=f'Fsw = {fs_sw/1e3:.1f} kHz')
        plt.axhline(-40, color='gray', linestyle='-.', linewidth=1.2, label='Rejeição = -40 dB')
        plt.ylabel('Magnitude (dB)', fontsize=FONT_LABEL)
        plt.grid(True, which="both", linestyle='--', alpha=0.7)
        plt.legend(loc='lower left', fontsize=FONT_LEGEND)
        plt.tick_params(axis='both', labelsize=FONT_TICKS)
        
        plt.subplot(2, 1, 2)
        plt.semilogx(freq_hz, phase, color='r', linewidth=2)
        plt.axvline(fc, color='darkorange', linestyle='--', linewidth=1.5, label=f'Fc = {fc/1e3:.1f} kHz')
        plt.axvline(fs_sw, color='red', linestyle=':', linewidth=1.5, label=f'Fsw = {fs_sw/1e3:.1f} kHz')
        plt.ylabel('Fase (graus)', fontsize=FONT_LABEL)
        plt.xlabel('Frequência (Hz)', fontsize=FONT_LABEL)
        plt.grid(True, which="both", linestyle='--', alpha=0.7)
        plt.legend(loc='lower left', fontsize=FONT_LEGEND)
        plt.tick_params(axis='both', labelsize=FONT_TICKS)
        
        plt.tight_layout()
        output_filename = "filtro_bode_continuo.png"
        plt.savefig(output_filename, dpi=DPI)
        plt.close()
        print(f"Gráfico do filtro contínuo salvo em '{output_filename}'.\n")
        
        print(f"Discretização Tustin (Ts = {ts * 1e6:.2f} us):")
        print(f"  - Numerador em z: {num_z}")
        print(f"  - Denominador em z: {den_z}\n")
        
        print("--- EQUAÇÃO DE DIFERENÇAS (TUSTIN) ---")
        print(
            f"y[k] = {b_coefs[0]:.6f} * x[k] "
            f"+ {b_coefs[1]:.6f} * x[k-1] "
            f"+ {b_coefs[2]:.6f} * x[k-2] "
            f"- ({a_coefs[1]:.6f}) * y[k-1] "
            f"- ({a_coefs[2]:.6f}) * y[k-2]\n"
        )
        
        componentes = {'R': r_val, 'C1': c1_val, 'C2': c2_val}
        return sys_cont, sys_disc, componentes

