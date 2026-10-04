import os
import json
import time
import threading
import glob
import queue
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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
        self.root.geometry("950x710")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Referência para armazenar o objeto do conversor ativo
        self.current_buck = None

        # =====================================================================
        # Filas e Buffers para recepção em tempo real
        # =====================================================================
        self.data_queue = queue.Queue()
        self.rx_time = []
        self.rx_iL = []
        self.rx_vC = []
        self.expected_steps = 0
        self.rt_window = None  # Referência para a nova janela

        # Configuração do Layout Principal com Largura Fixa na Sidebar
        self.left_frame = ttk.Frame(root, padding="10", width=290)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        self.left_frame.pack_propagate(False)

        self.right_frame = ttk.Frame(root, padding="10")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Variável para alternar o modo de instanciação
        self.mode_var = tk.StringVar(value="Parâmetros de Projeto")

        # Dicionários de Inputs para cada modo
        self.inputs_project = {
            "Vs [V]": tk.StringVar(value="50.0"),
            "Vo [V]": tk.StringVar(value="25.0"),
            "Po [W]": tk.StringVar(value="100.0"),
            "ΔiL [A]": tk.StringVar(value="0.2"),
            "ΔVo [V]": tk.StringVar(value="0.1"),
            "fs [Hz]": tk.StringVar(value="5000.0"),
            "N (f_sim = N * fs)": tk.StringVar(value="100"),
            "Tempo [ms]": tk.StringVar(value="20.0"),
        }

        self.inputs_components = {
            "Vs [V]": tk.StringVar(value="50.0"),
            "Vo [V]": tk.StringVar(value="25.0"),
            "R [Ω]": tk.StringVar(value="6.25"),
            "L [mH]": tk.StringVar(value="12.5"),
            "C [µF]": tk.StringVar(value="50.0"),
            "fs [Hz]": tk.StringVar(value="5000.0"),
            "N (f_sim = N * fs)": tk.StringVar(value="100"),
            "Tempo [ms]": tk.StringVar(value="20.0"),
        }

        self.target_device_var = tk.StringVar()
        self.cancel_flag = False  

        self._build_sidebar()
        self._build_plot_panel()

        # Vincula rastreio de alterações para atualizar simulação automaticamente
        self._trace_inputs()

        self.run_simulation()

    def on_closing(self):
        self.root.quit()
        self.root.destroy()
        os._exit(0)

    def _get_active_inputs(self) -> dict:
        if self.mode_var.get() == "Parâmetros de Projeto":
            return self.inputs_project
        else:
            return self.inputs_components

    def _trace_inputs(self):
        for var in self.inputs_project.values():
            var.trace_add("write", self.run_simulation)
        for var in self.inputs_components.values():
            var.trace_add("write", self.run_simulation)

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

    def _build_sidebar(self):
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

        ttk.Label(self.left_frame, text="Modo de Entrada", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        
        mode_combo = ttk.Combobox(
            self.left_frame,
            textvariable=self.mode_var,
            values=["Parâmetros de Projeto", "Componentes Físicos"],
            state="readonly"
        )
        mode_combo.pack(fill=tk.X, pady=(2, 8))
        
        self.mode_var.trace_add("write", lambda *args: self._rebuild_inputs_panel())
        self.inputs_container = ttk.Frame(self.left_frame)
        self.inputs_container.pack(fill=tk.X, pady=2)

        self._build_input_fields()

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
            wraplength=260,
            justify=tk.LEFT
        )
        self.lbl_status.pack(fill=tk.X, pady=(2, 5))

        self.results_var = tk.StringVar(value="")
        self.lbl_results = ttk.Label(
            self.left_frame, 
            textvariable=self.results_var, 
            justify=tk.LEFT,
            wraplength=260
        )
        self.lbl_results.pack(fill=tk.X, pady=5)

    def _build_input_fields(self):
        active_inputs = self._get_active_inputs()
        self.entries = {}
        for label_text, string_var in active_inputs.items():
            frame = ttk.Frame(self.inputs_container)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=label_text, width=16).pack(side=tk.LEFT)
            entry = ttk.Entry(frame, textvariable=string_var, width=10)
            entry.pack(side=tk.RIGHT)
            self.entries[label_text] = entry

    def _rebuild_inputs_panel(self):
        for widget in self.inputs_container.winfo_children():
            widget.destroy()
        self._build_input_fields()
        self.run_simulation()

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
        
        active_inputs = self._get_active_inputs()
        data_to_save = {key: var.get() for key, var in active_inputs.items()}
        data_to_save["mode"] = self.mode_var.get()
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
                
            if "mode" in loaded_data:
                self.mode_var.set(loaded_data["mode"])
                self._rebuild_inputs_panel()
                
            active_inputs = self._get_active_inputs()
            for key, value in loaded_data.items():
                if key in active_inputs:
                    active_inputs[key].set(value)
            
            if "target_device" in loaded_data:
                self.target_device_var.set(loaded_data["target_device"])
                
        except Exception as e:
            self.results_var.set(f"Erro ao carregar:\n{e}")
            self.lbl_results.config(foreground="red")

    def _show_loading_dialog(self):
        self.modal_dialog = tk.Toplevel(self.root)
        self.modal_dialog.title("Aguardando Dispositivo")
        self.modal_dialog.geometry("350x150")
        self.modal_dialog.resizable(False, False)
        
        self.modal_dialog.transient(self.root)
        self.modal_dialog.grab_set()

        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 175
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 75
        self.modal_dialog.geometry(f"+{x}+{y}")

        ttk.Label(
            self.modal_dialog, 
            text="⏳ Aguardando Configuração (ACK)...", 
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

        self.modal_dialog.protocol("WM_DELETE_WINDOW", lambda: None)

    def _close_loading_dialog(self):
        if hasattr(self, 'modal_dialog') and self.modal_dialog.winfo_exists():
            self.modal_dialog.grab_release()
            self.modal_dialog.destroy()

    def on_button_click(self):
        self.cancel_flag = True
        time.sleep(0.05)
        self.cancel_flag = False

        port = self.target_device_var.get()
        if not port or "Nenh" in port:
            self.status_var.set("Erro: Nenhum dispositivo selecionado!")
            self.lbl_status.config(foreground="red")
            return

        buck = self.run_simulation()
        if buck is None:
            self.status_var.set("Erro: Parâmetros inválidos no projeto ou DCM detectado.")
            self.lbl_status.config(foreground="red")
            return

        active_inputs = self._get_active_inputs()
        N = int(active_inputs["N (f_sim = N * fs)"].get())
        sim_time_ms = float(active_inputs["Tempo [ms]"].get())

        self.rx_time.clear()
        self.rx_iL.clear()
        self.rx_vC.clear()
        with self.data_queue.mutex:
            self.data_queue.queue.clear()

        self._show_loading_dialog()

        threading.Thread(
            target=self._send_and_receive_serial,
            args=(buck, N, sim_time_ms / 1000.0, port),
            daemon=True
        ).start()

    def _send_and_receive_serial(self, buck: BuckConverterCCM, N: int, sim_time: float, port: str):
        try:
            Ad_00, Ad_01, Bd1_0, Ad_10, Ad_11, Bd1_1, total_steps = buck.discretize_model(N, sim_time)
            fs_sim = N * buck.fs
            self.expected_steps = total_steps

            payload = f"CONFIG;{buck.Vs};{Ad_00};{Ad_01};{Bd1_0};{Ad_10};{Ad_11};{Bd1_1};{fs_sim};{total_steps}\n"

            with serial.Serial(port, 115200, timeout=0.1) as ser:
                ser.reset_input_buffer()
                ser.write(payload.encode('ascii'))
                ser.flush()

                while not self.cancel_flag:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if "OK" in line:
                            break
                    time.sleep(0.05)

                if self.cancel_flag:
                    self.root.after(0, lambda: self.status_var.set("Envio cancelado pelo utilizador."))
                    self.root.after(0, lambda: self.lbl_status.config(foreground="orange"))
                    return

                self.root.after(0, self._open_realtime_window)

                rx_buffer = ""
                received_count = 0

                while not self.cancel_flag and received_count < total_steps:
                    bytes_available = ser.in_waiting
                    if bytes_available > 0:
                        raw_bytes = ser.read(bytes_available)
                        rx_buffer += raw_bytes.decode('utf-8', errors='ignore')

                        while "\n" in rx_buffer:
                            line, rx_buffer = rx_buffer.split("\n", 1)
                            line = line.strip()

                            if line.startswith("DATA;"):
                                parts = line.split(";")
                                if len(parts) == 5:
                                    _, k, elapsed, val_iL, val_vC = parts
                                    self.data_queue.put((float(elapsed), float(val_iL), float(val_vC)))
                                    received_count += 1
                    else:
                        time.sleep(0.001)

                while not self.data_queue.empty() and not self.cancel_flag:
                    time.sleep(0.01)

                if received_count >= total_steps:
                    self.root.after(0, lambda: self.status_var.set("Sucesso: Transmissão Serial Concluída!"))
                    self.root.after(0, lambda: self.lbl_status.config(foreground="green"))

        except Exception as err:
            self.root.after(0, lambda: self.status_var.set(f"Erro Serial: {err}"))
            self.root.after(0, lambda: self.lbl_status.config(foreground="red"))
        
        finally:
            self.root.after(0, self._close_loading_dialog)

    def _open_realtime_window(self):
        self._close_loading_dialog()

        if self.rt_window is not None and self.rt_window.winfo_exists():
            self.rt_window.destroy()

        self.rt_window = tk.Toplevel(self.root)
        self.rt_window.title("Monitoramento Serial - Em Tempo Real")
        self.rt_window.geometry("850x650")

        def on_rt_close():
            self.cancel_flag = True 
            if self.rt_window is not None:
                self.rt_window.destroy()
                self.rt_window = None

        self.rt_window.protocol("WM_DELETE_WINDOW", on_rt_close)

        toolbar_frame = ttk.Frame(self.rt_window, padding="5")
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)

        btn_save_csv = ttk.Button(
            toolbar_frame, 
            text="Salvar Dados Recebidos (CSV)", 
            command=self._save_realtime_data
        )
        btn_save_csv.pack(side=tk.RIGHT, padx=5)

        self.rt_fig, (self.rt_ax1, self.rt_ax2) = plt.subplots(2, 1, figsize=(8, 6))
        self.rt_fig.tight_layout(pad=3.0)

        self.rt_canvas = FigureCanvasTkAgg(self.rt_fig, master=self.rt_window)
        self.rt_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.root.after(30, self._update_realtime_plot)

    def _save_realtime_data(self):
        if not self.rx_time:
            messagebox.showwarning("Aviso", "Não há dados recebidos para salvar.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Arquivo CSV", "*.csv"), ("Todos os arquivos", "*.*")],
            title="Salvar Curvas Recebidas"
        )
        if not filepath:
            return

        try:
            with open(filepath, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=',')
                writer.writerow(["Tempo [ms]", "iL [A]", "vC [V]"])
                
                for t, il, vc in zip(self.rx_time, self.rx_iL, self.rx_vC):
                    writer.writerow([f"{t:.6f}", f"{il:.6f}", f"{vc:.6f}"])
                    
            self.status_var.set(f"Sucesso: Dados exportados para {os.path.basename(filepath)}.")
            self.lbl_status.config(foreground="green")
        except Exception as e:
            self.status_var.set(f"Erro ao salvar CSV: {e}")
            self.lbl_status.config(foreground="red")

    def _update_realtime_plot(self):
        if self.rt_window is None or not self.rt_window.winfo_exists():
            return  

        has_new_data = False

        while not self.data_queue.empty():
            try:
                t_val, iL_val, vC_val = self.data_queue.get_nowait()
                
                # Acessa o Vs diretamente através do objeto buck armazenado na GUI
                Vs = self.current_buck.Vs if self.current_buck else float(self._get_active_inputs()["Vs [V]"].get())
                dac_max = 3.3
                
                # Fator de conversão inverso (de DAC para Físico)
                scale_factor = Vs / dac_max
                
                self.rx_time.append(t_val * 1e3) 
                self.rx_iL.append(iL_val * scale_factor)
                self.rx_vC.append(vC_val * scale_factor)
                has_new_data = True
            except queue.Empty:
                break

        if has_new_data:
            self.rt_ax1.clear()
            self.rt_ax1.plot(self.rx_time, self.rx_iL, linewidth=1.2, color="tab:blue")
            self.rt_ax1.set_ylabel(r"$i_L$ (A)")
            self.rt_ax1.grid(True, linestyle="--", alpha=0.5)

            self.rt_ax2.clear()
            self.rt_ax2.plot(self.rx_time, self.rx_vC, linewidth=1.2, color="tab:orange")
            self.rt_ax2.set_xlabel("Tempo (ms)")
            self.rt_ax2.set_ylabel(r"$v_C$ (V)")
            self.rt_ax2.grid(True, linestyle="--", alpha=0.5)

            self.rt_canvas.draw_idle()

        if len(self.rx_time) < self.expected_steps:
            self.root.after(30, self._update_realtime_plot)

    def run_simulation(self, *args) -> BuckConverterCCM | None:
        try:
            mode = self.mode_var.get()
            
            if mode == "Parâmetros de Projeto":
                Vs = float(self.inputs_project["Vs [V]"].get())
                Vo = float(self.inputs_project["Vo [V]"].get())
                Po = float(self.inputs_project["Po [W]"].get())
                delta_iL = float(self.inputs_project["ΔiL [A]"].get())
                delta_Vo = float(self.inputs_project["ΔVo [V]"].get())
                fs = float(self.inputs_project["fs [Hz]"].get())
                N = int(self.inputs_project["N (f_sim = N * fs)"].get())
                sim_time_ms = float(self.inputs_project["Tempo [ms]"].get())

                buck = BuckConverterCCM.from_design_parameters(
                    Vs=Vs, Vo=Vo, Po=Po, delta_iL=delta_iL, delta_Vo=delta_Vo, fs=fs
                )
            else:
                Vs = float(self.inputs_components["Vs [V]"].get())
                Vo = float(self.inputs_components["Vo [V]"].get())
                R = float(self.inputs_components["R [Ω]"].get())
                L = float(self.inputs_components["L [mH]"].get()) * 1e-3 
                C = float(self.inputs_components["C [µF]"].get()) * 1e-6 
                fs = float(self.inputs_components["fs [Hz]"].get())
                N = int(self.inputs_components["N (f_sim = N * fs)"].get())
                sim_time_ms = float(self.inputs_components["Tempo [ms]"].get())

                buck = BuckConverterCCM.from_circuit_components(
                    Vs=Vs, Vo=Vo, R=R, L=L, C=C, fs=fs
                )

            # Armazena o conversor atual na instância da GUI
            self.current_buck = buck

            res_text = (
                f"Resultados ({'Projeto' + (' [CCM]' if buck.L > buck.Lmin else ' [DCM!]') if mode=='Parâmetros de Projeto' else 'Componentes'}):\n"
                "-----------------\n"
                f"L = {buck.L * 1e6:.2f} µH\n"
                f"C = {buck.C * 1e6:.2f} µF\n"
                f"R = {buck.R:.2f} Ω\n"
                f"Lmin = {buck.Lmin * 1e6:.2f} µH\n"
                f"D = {buck.D:.3f}\n"
                f"Alvo: {self.target_device_var.get()}"
            )
            self.results_var.set(res_text)
            self.lbl_results.config(foreground="black")

            time_vec, iL, vC = buck.simulate(N=N, sim_time=sim_time_ms / 1000.0)

            self.ax1.clear()
            self.ax1.plot(time_vec * 1e3, iL, linewidth=1.2, color="tab:blue")
            self.ax1.set_title("Corrente no Indutor (Teórico)")
            self.ax1.set_xlabel("Tempo (ms)")
            self.ax1.set_ylabel(r"$i_L$ (A)")
            self.ax1.grid(True, linestyle="--", alpha=0.5)

            self.ax2.clear()
            self.ax2.plot(time_vec * 1e3, vC, linewidth=1.2, color="tab:orange")
            self.ax2.set_title("Tensão de Saída (Teórico)")
            self.ax2.set_xlabel("Tempo (ms)")
            self.ax2.set_ylabel(r"$v_C$ (V)")
            self.ax2.grid(True, linestyle="--", alpha=0.5)

            self.fig.tight_layout()
            self.canvas.draw()

            return buck

        except CCMError:
            self.current_buck = None
            self.results_var.set("Erro: Operação em DCM detectada!\n(L <= Lmin)")
            self.lbl_results.config(foreground="red")
            self.ax1.clear()
            self.ax2.clear()
            self.canvas.draw()
            return None
            
        except ValueError:
            self.current_buck = None
            self.results_var.set("Aguardando entrada válida...")
            self.lbl_results.config(foreground="orange")
            return None