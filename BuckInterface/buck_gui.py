import os
import json
import tkinter as tk
from tkinter import ttk, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from buck_converter import BuckConverterCCM, CCMError

class BuckSimulatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador Conversor Buck CCM")
        self.root.geometry("900x600")

        # Gerencia o evento de fechar a janela no "X" para matar o processo
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Configuração do Layout Principal
        self.left_frame = ttk.Frame(root, padding="10")
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.right_frame = ttk.Frame(root, padding="10")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Variáveis de Entrada
        self.inputs = {
            "Vs [V]": tk.StringVar(value="50.0"),
            "Vo [V]": tk.StringVar(value="25.0"),
            "Po [W]": tk.StringVar(value="100.0"),
            "ΔiL [%]": tk.StringVar(value="0.2"),
            "ΔVo [%]": tk.StringVar(value="0.1"),
            "fs [Hz]": tk.StringVar(value="5000.0"),
            "N (f_sim = N * fs)": tk.StringVar(value="100"),
            "Tempo [ms]": tk.StringVar(value="20.0"),
        }

        self._build_input_panel()
        self._build_plot_panel()

        # Adiciona um gatilho para rodar a simulação a cada alteração de texto
        for var in self.inputs.values():
            var.trace_add("write", self.run_simulation)

        # Roda a simulação inicial ao abrir
        self.run_simulation()

    def on_closing(self):
        """Encerra a aplicação completamente ao fechar a janela sem causar erros no Tkinter."""
        self.root.quit()     # Para o mainloop do Tkinter
        self.root.destroy()  # Destrói todos os widgets
        os._exit(0)          # Mata o processo limpo e direto pelo Sistema Operacional

    def _build_input_panel(self):
        ttk.Label(self.left_frame, text="Parâmetros de Projeto", font=("Arial", 10, "bold")).pack(pady=(0, 10))

        # Criação dos campos de texto (Entry) e Labels
        self.entries = {}
        for label_text, string_var in self.inputs.items():
            frame = ttk.Frame(self.left_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=label_text, width=15).pack(side=tk.LEFT)
            entry = ttk.Entry(frame, textvariable=string_var, width=10)
            entry.pack(side=tk.RIGHT)
            self.entries[label_text] = entry

        # Botão de Simulação
        self.btn_run = ttk.Button(self.left_frame, text="Executar Simulação", command=self.on_button_click)
        self.btn_run.pack(fill=tk.X, pady=(20, 5))

        # Frame para os botões de Salvar e Carregar
        file_btn_frame = ttk.Frame(self.left_frame)
        file_btn_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.btn_save = ttk.Button(file_btn_frame, text="Salvar Config.", command=self.save_config)
        self.btn_save.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        
        self.btn_load = ttk.Button(file_btn_frame, text="Carregar Config.", command=self.load_config)
        self.btn_load.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(2, 0))

        # Painel de Resultados Calculados
        self.results_var = tk.StringVar(value="")
        self.lbl_results = ttk.Label(self.left_frame, textvariable=self.results_var, justify=tk.LEFT)
        self.lbl_results.pack(fill=tk.X, pady=5)

    def _build_plot_panel(self):
        # Cria a figura e os eixos do Matplotlib
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(6, 5))
        self.fig.tight_layout(pad=3.0)

        # Integra a figura do Matplotlib ao Tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def save_config(self):
        """Abre uma janela para salvar os parâmetros atuais em um arquivo JSON."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Arquivos JSON", "*.json"), ("Todos os arquivos", "*.*")],
            title="Salvar Configuração"
        )
        if not filepath:
            return # Usuário cancelou
        
        # Extrai os valores atuais do dicionário de inputs
        data_to_save = {key: var.get() for key, var in self.inputs.items()}
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4)
        except Exception as e:
            self.results_var.set(f"Erro ao salvar:\n{e}")
            self.lbl_results.config(foreground="red")

    def load_config(self):
        """Abre uma janela para carregar parâmetros de um arquivo JSON."""
        filepath = filedialog.askopenfilename(
            filetypes=[("Arquivos JSON", "*.json"), ("Todos os arquivos", "*.*")],
            title="Carregar Configuração"
        )
        if not filepath:
            return # Usuário cancelou
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                
            # Atualiza as variáveis (isso vai engatilhar o run_simulation automaticamente)
            for key, value in loaded_data.items():
                if key in self.inputs:
                    self.inputs[key].set(value)
                    
        except Exception as e:
            self.results_var.set(f"Erro ao carregar:\n{e}")
            self.lbl_results.config(foreground="red")

    def on_button_click(self):
        # Ação acionada quando o botão é efetivamente clicado
        print("Botão 'Executar Simulação' foi clicado!")

    def run_simulation(self, *args):
        # O *args captura os argumentos enviados pelo trace_add da StringVar
        try:
            # Captura os dados da interface
            Vs = float(self.inputs["Vs [V]"].get())
            Vo = float(self.inputs["Vo [V]"].get())
            Po = float(self.inputs["Po [W]"].get())
            delta_iL = float(self.inputs["ΔiL [A]"].get())
            delta_Vo = float(self.inputs["ΔVo [V]"].get())
            fs = float(self.inputs["fs [Hz]"].get())
            N = int(self.inputs["N (f_sim = N * fs)"].get())
            sim_time_ms = float(self.inputs["Tempo [ms]"].get())

            # Projeto
            buck = BuckConverterCCM.from_design_parameters(
                Vs=Vs, Vo=Vo, Po=Po, delta_iL=delta_iL, delta_Vo=delta_Vo, fs=fs
            )

            # Atualiza o painel de resultados na tela
            res_text = (
                "Resultados (CCM):\n"
                "-----------------\n"
                f"L = {buck.L * 1e6:.2f} µH\n"
                f"C = {buck.C * 1e6:.2f} µF\n"
                f"R = {buck.R:.2f} Ω\n"
                f"D = {buck.D:.3f}"
            )
            self.results_var.set(res_text)
            self.lbl_results.config(foreground="black")

            # Simulação
            time, iL, vC = buck.simulate(N=N, sim_time=sim_time_ms / 1000.0)

            # Atualiza Gráfico de Corrente
            self.ax1.clear()
            self.ax1.plot(time * 1e3, iL, linewidth=1.2, color="tab:blue")
            self.ax1.set_title("Corrente no Indutor")
            self.ax1.set_xlabel("Tempo (ms)")
            self.ax1.set_ylabel(r"$i_L$ (A)")
            self.ax1.grid(True, linestyle="--", alpha=0.5)

            # Atualiza Gráfico de Tensão
            self.ax2.clear()
            self.ax2.plot(time * 1e3, vC, linewidth=1.2, color="tab:orange")
            self.ax2.set_title("Tensão de Saída")
            self.ax2.set_xlabel("Tempo (ms)")
            self.ax2.set_ylabel(r"$v_C$ (V)")
            self.ax2.grid(True, linestyle="--", alpha=0.5)

            # Desenha os gráficos atualizados no Canvas
            self.fig.tight_layout()
            self.canvas.draw()

        except CCMError as e:
            self.results_var.set("Erro: Operação em DCM detectada!")
            self.lbl_results.config(foreground="red")
            
            # Limpa os gráficos para evitar confusão de dados incorretos
            self.ax1.clear()
            self.ax2.clear()
            self.canvas.draw()
            
        except ValueError:
            # Ocorre temporariamente ao digitar (ex: se o usuário apagar todo o texto antes de digitar o novo número)
            self.results_var.set("Aguardando entrada válida...")
            self.lbl_results.config(foreground="orange")