import os
import json
import time
import threading
import glob
import tkinter as tk
from tkinter import ttk, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import serial
import serial.tools.list_ports

from buck_converter import BuckConverterCCM, CCMError

IS_TEST_MODE = True


class BuckSimulatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador Conversor Buck CCM")
        self.root.geometry("950x670")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Configuração do Layout Principal com Largura Fixa na Sidebar
        self.left_frame = ttk.Frame(root, padding="10", width=280)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        self.left_frame.pack_propagate(False)

        self.right_frame = ttk.Frame(root, padding="10")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.inputs = {
            "Vs [V]": tk.StringVar(value="50.0"),
            "Vo [V]": tk.StringVar(value="25.0"),
            "Po [W]": tk.StringVar(value="100.0"),
            "ΔiL [A]": tk.StringVar(value="0.2"),
            "ΔVo [V]": tk.StringVar(value="0.1"),
            "fs [Hz]": tk.StringVar(value="5000.0"),
            "N (f_sim = N * fs)": tk.StringVar(value="100"),
            "Tempo [ms]": tk.StringVar(value="20.0"),
        }

        self.target_device_var = tk.StringVar()
        self.cancel_flag = False  # Controle para cancelar espera manual

        self._build_input_panel()
        self._build_plot_panel()

        for var in self.inputs.values():
            var.trace_add("write", self.run_simulation)

        self.run_simulation()

    def on_closing(self):
        self.root.quit()
        self.root.destroy()
        os._exit(0)

    def _get_available_devices(self) -> list[str]:
        if IS_TEST_MODE:
            virtual_ports = sorted(glob.glob("/tmp/ttyVirtual*"))
            if virtual_ports:
                return virtual_ports
            return ["Nenhuma porta virtual ativa (Ligue o socat)"]

        ports = serial.tools.list_ports.comports()
        devices = [p.device for p in ports]
        return devices if devices else ["Nenhum dispositivo encontrado"]

    def refresh_devices(self):
        devices = self._get_available_devices()
        self.combo_device["values"] = devices
        if devices:
            self.combo_device.current(0)

    def _build_input_panel(self):
        mode_str = "TESTE (Virtual)" if IS_TEST_MODE else "DEPLOY (Hardware Real)"
        ttk.Label(
            self.left_frame, 
            text=f"Dispositivo Alvo [{mode_str}]", 
            font=("Arial", 9, "bold")
        ).pack(fill=tk.X, pady=(0, 2))

        dev_frame = ttk.Frame(self.left_frame)
        dev_frame.pack(fill=tk.X, pady=(0, 5))

        self.combo_device = ttk.Combobox(
            dev_frame, 
            textvariable=self.target_device_var, 
            state="readonly"
        )
        self.combo_device.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        btn_refresh = ttk.Button(dev_frame, text="🔄", width=3, command=self.refresh_devices)
        btn_refresh.pack(side=tk.RIGHT)

        self.refresh_devices()

        ttk.Separator(self.left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        ttk.Label(self.left_frame, text="Parâmetros de Projeto", font=("Arial", 10, "bold")).pack(pady=(5, 5))

        self.entries = {}
        for label_text, string_var in self.inputs.items():
            frame = ttk.Frame(self.left_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=label_text, width=15).pack(side=tk.LEFT)
            entry = ttk.Entry(frame, textvariable=string_var, width=10)
            entry.pack(side=tk.RIGHT)
            self.entries[label_text] = entry

        self.btn_run = ttk.Button(
            self.left_frame, 
            text="Executar Simulação e Enviar", 
            command=self.on_button_click
        )
        self.btn_run.pack(fill=tk.X, pady=(15, 5))

        file_btn_frame = ttk.Frame(self.left_frame)
        file_btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_save = ttk.Button(file_btn_frame, text="Salvar Config.", command=self.save_config)
        self.btn_save.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        
        self.btn_load = ttk.Button(file_btn_frame, text="Carregar Config.", command=self.load_config)
        self.btn_load.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(2, 0))

        self.status_var = tk.StringVar(value="Status: Aguardando envio...")
        self.lbl_status = ttk.Label(
            self.left_frame, 
            textvariable=self.status_var, 
            font=("Arial", 9, "bold"),
            foreground="blue",
            wraplength=250,
            justify=tk.LEFT
        )
        self.lbl_status.pack(fill=tk.X, pady=(2, 5))

        self.results_var = tk.StringVar(value="")
        self.lbl_results = ttk.Label(
            self.left_frame, 
            textvariable=self.results_var, 
            justify=tk.LEFT,
            wraplength=250
        )
        self.lbl_results.pack(fill=tk.X, pady=5)

    def _build_plot_panel(self):
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(6, 5))
        self.fig.tight_layout(pad=3.0)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def save_config(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Arquivos JSON", "*.json"), ("Todos os arquivos", "*.*")],
            title="Salvar Configuração"
        )
        if not filepath:
            return
        
        data_to_save = {key: var.get() for key, var in self.inputs.items()}
        data_to_save["target_device"] = self.target_device_var.get()
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4)
        except Exception as e:
            self.results_var.set(f"Erro ao salvar:\n{e}")
            self.lbl_results.config(foreground="red")

    def load_config(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Arquivos JSON", "*.json"), ("Todos os arquivos", "*.*")],
            title="Carregar Configuração"
        )
        if not filepath:
            return
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                
            for key, value in loaded_data.items():
                if key in self.inputs:
                    self.inputs[key].set(value)
            
            if "target_device" in loaded_data:
                self.target_device_var.set(loaded_data["target_device"])
                    
        except Exception as e:
            self.results_var.set(f"Erro ao carregar:\n{e}")
            self.lbl_results.config(foreground="red")

    def _show_loading_dialog(self):
        """Cria uma janela pop-up MODAL que bloqueia a interface principal enquanto aguarda."""
        self.modal_dialog = tk.Toplevel(self.root)
        self.modal_dialog.title("Aguardando Dispositivo")
        self.modal_dialog.geometry("350x150")
        self.modal_dialog.resizable(False, False)
        
        # Faz a janela ficar por cima e bloqueia cliques na janela principal
        self.modal_dialog.transient(self.root)
        self.modal_dialog.grab_set()

        # Centraliza o pop-up
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 175
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 75
        self.modal_dialog.geometry(f"+{x}+{y}")

        ttk.Label(
            self.modal_dialog, 
            text="⏳ Aguardando Configuração...\nEnviado pacote para o dispositivo.", 
            font=("Arial", 10, "bold"),
            justify=tk.CENTER
        ).pack(pady=15)

        progress = ttk.Progressbar(self.modal_dialog, mode="indeterminate")
        progress.pack(fill=tk.X, padx=20, pady=5)
        progress.start(10)

        self.cancel_flag = False
        def cancel_action():
            self.cancel_flag = True
            self._close_loading_dialog()

        btn_cancel = ttk.Button(self.modal_dialog, text="Cancelar", command=cancel_action)
        btn_cancel.pack(pady=10)

        # Desabilita o botão 'X' da janela modal para forçar a usar o botão Cancelar
        self.modal_dialog.protocol("WM_DELETE_WINDOW", lambda: None)

    def _close_loading_dialog(self):
        """Fecha a janela modal e devolve o foco para a GUI principal."""
        if hasattr(self, 'modal_dialog') and self.modal_dialog.winfo_exists():
            self.modal_dialog.grab_release()
            self.modal_dialog.destroy()

    def on_button_click(self):
        port = self.target_device_var.get()
        if not port or "Nenh" in port:
            self.status_var.set("Erro: Nenhum dispositivo selecionado!")
            self.lbl_status.config(foreground="red")
            return

        buck = self.run_simulation()
        if buck is None:
            self.status_var.set("Erro: Parâmetros inválidos no projeto.")
            self.lbl_status.config(foreground="red")
            return

        N = int(self.inputs["N (f_sim = N * fs)"].get())
        sim_time_ms = float(self.inputs["Tempo [ms]"].get())

        # Exibe o pop-up bloqueante
        self._show_loading_dialog()

        # Dispara a thread de envio
        threading.Thread(
            target=self._send_config_parameters,
            args=(buck, N, sim_time_ms / 1000.0, port),
            daemon=True
        ).start()

    def _send_config_parameters(self, buck: BuckConverterCCM, N: int, sim_time: float, port: str):
        """Envia os dados e FICA TRAVADO esperando a resposta 'OK' sem timeout fixo curto."""
        try:
            Ad_00, Ad_01, Bd1_0, Ad_10, Ad_11, Bd1_1, total_steps = buck.discretize_model(N, sim_time)
            payload = f"CONFIG;{Ad_00};{Ad_01};{Bd1_0};{Ad_10};{Ad_11};{Bd1_1};{buck.fs};{total_steps}\n"

            # Timeout baixo na porta serial para poder checar o botão 'Cancelar' sem travar a thread
            with serial.Serial(port, 115200, timeout=0.2) as ser:
                ser.reset_input_buffer()
                ser.write(payload.encode('ascii'))
                ser.flush()

                # FICA EM LOOP BLOQUEADO até receber o "OK" ou o usuário cancelar
                response = ""
                while not self.cancel_flag:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if "OK" in line:
                            response = line
                            break

                    time.sleep(0.05)

                # Atualiza a interface gráfica via thread principal
                if self.cancel_flag:
                    self.root.after(0, lambda: self.status_var.set("Envio cancelado pelo usuário."))
                    self.root.after(0, lambda: self.lbl_status.config(foreground="orange"))
                elif "OK" in response:
                    self.root.after(0, lambda: self.status_var.set("Sucesso: Dispositivo Configurado!"))
                    self.root.after(0, lambda: self.lbl_status.config(foreground="green"))

        except Exception as err:
            self.root.after(0, lambda: self.status_var.set(f"Erro Serial: {err}"))
            self.root.after(0, lambda: self.lbl_status.config(foreground="red"))
        
        finally:
            # Garante o fechamento da janela modal bloqueante
            self.root.after(0, self._close_loading_dialog)

    def run_simulation(self, *args) -> BuckConverterCCM | None:
        try:
            Vs = float(self.inputs["Vs [V]"].get())
            Vo = float(self.inputs["Vo [V]"].get())
            Po = float(self.inputs["Po [W]"].get())
            delta_iL = float(self.inputs["ΔiL [A]"].get())
            delta_Vo = float(self.inputs["ΔVo [V]"].get())
            fs = float(self.inputs["fs [Hz]"].get())
            N = int(self.inputs["N (f_sim = N * fs)"].get())
            sim_time_ms = float(self.inputs["Tempo [ms]"].get())

            buck = BuckConverterCCM.from_design_parameters(
                Vs=Vs, Vo=Vo, Po=Po, delta_iL=delta_iL, delta_Vo=delta_Vo, fs=fs
            )

            res_text = (
                "Resultados (CCM):\n"
                "-----------------\n"
                f"L = {buck.L * 1e6:.2f} µH\n"
                f"C = {buck.C * 1e6:.2f} µF\n"
                f"R = {buck.R:.2f} Ω\n"
                f"D = {buck.D:.3f}\n"
                f"Alvo: {self.target_device_var.get()}"
            )
            self.results_var.set(res_text)
            self.lbl_results.config(foreground="black")

            time_vec, iL, vC = buck.simulate(N=N, sim_time=sim_time_ms / 1000.0)

            self.ax1.clear()
            self.ax1.plot(time_vec * 1e3, iL, linewidth=1.2, color="tab:blue")
            self.ax1.set_title("Corrente no Indutor")
            self.ax1.set_xlabel("Tempo (ms)")
            self.ax1.set_ylabel(r"$i_L$ (A)")
            self.ax1.grid(True, linestyle="--", alpha=0.5)

            self.ax2.clear()
            self.ax2.plot(time_vec * 1e3, vC, linewidth=1.2, color="tab:orange")
            self.ax2.set_title("Tensão de Saída")
            self.ax2.set_xlabel("Tempo (ms)")
            self.ax2.set_ylabel(r"$v_C$ (V)")
            self.ax2.grid(True, linestyle="--", alpha=0.5)

            self.fig.tight_layout()
            self.canvas.draw()

            return buck

        except CCMError:
            self.results_var.set("Erro: Operação em DCM detectada!")
            self.lbl_results.config(foreground="red")
            self.ax1.clear()
            self.ax2.clear()
            self.canvas.draw()
            return None
            
        except ValueError:
            self.results_var.set("Aguardando entrada válida...")
            self.lbl_results.config(foreground="orange")
            return None
