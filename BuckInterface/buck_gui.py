import os
import json
import time
import threading
import glob
import queue
import csv
import struct
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import serial
import serial.tools.list_ports

from buck_converter import BuckConverterCCM, CCMError

IS_TEST_MODE = False
DEBUG_MODE = True  # Exibe mensagens essenciais de status no terminal
MAX_MS_LOCAL_SIM = 1000

# Definições do Protocolo Serial
HEADER_CONFIG         = 0x0001
HEADER_CONFIG_SUCCESS = 0x0002
HEADER_CONFIG_FAIL    = 0x0003
HEADER_DATA           = 0x0004
HEADER_SIMULATION_END = 0x0005


class BuckSimulatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador Conversor Buck CCM - STM32H7")
        self.root.geometry("950x710")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.current_buck = None
        self._status_timer = None

        # Filas e Buffers de Recepção
        self.data_queue = queue.Queue()
        self.rx_time = []
        self.rx_iL = []
        self.rx_vC = []
        self.expected_steps = 0
        self.received_count = 0
        self.rt_window = None

        # Objetos de linha do Matplotlib (para atualização rápida)
        self.line_iL = None
        self.line_vC = None

        # Layout Principal
        self.left_frame = ttk.Frame(root, padding="10", width=290)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)
        self.left_frame.pack_propagate(False)

        self.right_frame = ttk.Frame(root, padding="10")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.mode_var = tk.StringVar(value="Parâmetros de Projeto")

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
        self._trace_inputs()

        self.run_simulation()

    def set_temporary_status(self, text: str, color: str = "black", timeout_ms: int = 5000):
        if self._status_timer is not None:
            self.root.after_cancel(self._status_timer)
            self._status_timer = None

        self.status_var.set(text)
        self.lbl_status.config(foreground=color)

        if timeout_ms > 0:
            self._status_timer = self.root.after(
                timeout_ms, lambda: self.status_var.set("")
            )

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
        devices = []
        
        for p in ports:
            is_st = (p.vid == 0x0483) or \
                    (p.manufacturer and "STMicroelectronics" in p.manufacturer) or \
                    (p.description and "STM32" in p.description) or \
                    ("ttyACM" in p.device) or ("ttyUSB" in p.device)
            
            if is_st:
                devices.append(p.device)
                
        return devices if devices else ["Nenhum dispositivo encontrado"]

    def refresh_devices(self):
        devices = self._get_available_devices()
        self.combo_device["values"] = devices
        if devices:
            self.combo_device.current(0)

    def _build_sidebar(self):
        ttk.Label(
            self.left_frame, 
            text="Dispositivo Alvo", 
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
            text="Executar Simulação", 
            command=self.on_button_click
        )
        self.btn_run.pack(fill=tk.X, pady=(15, 5))

        file_btn_frame = ttk.Frame(self.left_frame)
        file_btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_save = ttk.Button(file_btn_frame, text="Salvar Config.", command=self.save_config)
        self.btn_save.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        
        self.btn_load = ttk.Button(file_btn_frame, text="Carregar Config.", command=self.load_config)
        self.btn_load.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(2, 0))

        self.status_var = tk.StringVar(value="")
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
            text="⏳ Transmitindo e aguardando resposta...", 
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
        if not port or "Nenhum" in port:
            self.set_temporary_status("Erro: Nenhum dispositivo selecionado!", "red", 4000)
            return

        buck = self.run_simulation()
        if buck is None:
            self.set_temporary_status("Erro: Parâmetros inválidos no projeto ou DCM detectado.", "red", 5000)
            return

        active_inputs = self._get_active_inputs()
        N = int(active_inputs["N (f_sim = N * fs)"].get())
        sim_time_ms = float(active_inputs["Tempo [ms]"].get())

        self.rx_time.clear()
        self.rx_iL.clear()
        self.rx_vC.clear()
        self.received_count = 0
        with self.data_queue.mutex:
            self.data_queue.queue.clear()

        self._show_loading_dialog()

        # Envia o tempo digitado (em segundos) diretamente para a thread serial
        threading.Thread(
            target=self._send_and_receive_serial,
            args=(buck, N, sim_time_ms / 1000.0, port),
            daemon=True
        ).start()

    def _send_and_receive_serial(self, buck: BuckConverterCCM, N: int, sim_time: float, port: str):
        try:
            # Calcula total_steps com base no tempo total digitado
            Ad_00, Ad_01, Bd1_0, Ad_10, Ad_11, Bd1_1, fs_sim, total_steps = buck.discretize_model(N, sim_time)
            self.expected_steps = total_steps
            self.received_count = 0

            vO_max = buck.Vs
            iL_max = (buck.Vs / buck.R) * 2.0
            
            # CORREÇÃO: Envia buck.fs (frequência nominal 5000 Hz) porque o MCU multiplica por N internamente
            payload = struct.pack(
                "<H9f2I",
                HEADER_CONFIG,
                float(vO_max),
                float(iL_max),
                float(Ad_00),
                float(Ad_01),
                float(Bd1_0),
                float(Ad_10),
                float(Ad_11),
                float(Bd1_1),
                float(buck.fs),  # <--- Frequência nominal fs (ex: 5000 Hz)
                int(N),
                int(total_steps) # total_steps correspondente ao tempo digitado
            )

            if DEBUG_MODE:
                print(f"\n[DEBUG] Conectando à porta {port}...")
                print(f"[DEBUG] Enviando CONFIG ({len(payload)} bytes): fs={buck.fs} Hz, N={N}, sim_time={sim_time*1e3:.1f}ms, total_steps={total_steps}")

            with serial.Serial(port, 115200, timeout=1.0) as ser:
                ser.reset_input_buffer()
                ser.write(payload)
                ser.flush()

                simulacao_rodando = True

                while simulacao_rodando and self.received_count < total_steps and not self.cancel_flag:
                    header_bytes = ser.read(2)
                    if len(header_bytes) < 2:
                        continue

                    header = struct.unpack("<H", header_bytes)[0]

                    if header == HEADER_CONFIG_SUCCESS:
                        if DEBUG_MODE:
                            print("[MCU] -> CONFIG_SUCCESS: Simulação aceita pelo firmware!")
                        self.root.after(0, self._open_realtime_window)

                    elif header == HEADER_CONFIG_FAIL:
                        if DEBUG_MODE:
                            print("[MCU] -> CONFIG_FAIL: Configuração rejeitada!")
                        self.root.after(0, lambda: self.set_temporary_status("Erro: Configuração rejeitada pelo MCU.", "red", 5000))
                        break

                    elif header == HEADER_DATA:
                        payload_bytes = ser.read(12)
                        if len(payload_bytes) == 12:
                            k_val, iL_val, vC_val = struct.unpack("<I2f", payload_bytes)
                            t_elapsed = k_val / (buck.fs * N)  # fs_sim = buck.fs * N (frequência real de amostragem no MCU)
                            self.data_queue.put((t_elapsed, iL_val, vC_val))
                            self.received_count += 1
                        else:
                            if DEBUG_MODE:
                                print("[MCU] -> Pacote DATA incompleto!")
                            break

                    elif header == HEADER_SIMULATION_END:
                        if DEBUG_MODE:
                            print("[MCU] -> SIMULATION_END: Fim da execução!")
                        simulacao_rodando = False
                        break

                    else:
                        if DEBUG_MODE:
                            print(f"[MCU] -> Header Desconhecido: 0x{header:04X}")

                if self.received_count >= total_steps or not simulacao_rodando:
                    if DEBUG_MODE:
                        print(f"[DEBUG] Transmissão concluída com sucesso ({self.received_count} amostras).")
                    self.root.after(0, lambda: self.set_temporary_status("Sucesso: Transmissão Serial Concluída!", "green", 5000))

        except Exception as err:
            err_msg = str(err)
            if DEBUG_MODE:
                print(f"[EXCEÇÃO SERIAL] {err_msg}")
            self.root.after(0, lambda e=err_msg: self.set_temporary_status(f"Erro Serial: {e}", "red", 6000))
        
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

        self.line_iL, = self.rt_ax1.plot([], [], linewidth=1.2, color="tab:blue")
        self.rt_ax1.set_ylabel(r"$i_L$ (A)")
        self.rt_ax1.grid(True, linestyle="--", alpha=0.5)

        self.line_vC, = self.rt_ax2.plot([], [], linewidth=1.2, color="tab:orange")
        self.rt_ax2.set_xlabel("Tempo (ms)")
        self.rt_ax2.set_ylabel(r"$v_C$ (V)")
        self.rt_ax2.grid(True, linestyle="--", alpha=0.5)

        self.rt_canvas = FigureCanvasTkAgg(self.rt_fig, master=self.rt_window)
        self.rt_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.root.after(50, self._update_realtime_plot)

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
                    
            self.set_temporary_status(f"Sucesso: Dados exportados para {os.path.basename(filepath)}.", "green", 4000)
        except Exception as e:
            self.set_temporary_status(f"Erro ao salvar CSV: {e}", "red", 5000)

    def _update_realtime_plot(self):
        if self.rt_window is None or not self.rt_window.winfo_exists():
            return  

        has_new_data = False

        while not self.data_queue.empty():
            try:
                t_val, iL_val, vC_val = self.data_queue.get_nowait()
                # Recebe e plota todas as amostras
                self.rx_time.append(t_val * 1e3) 
                self.rx_iL.append(iL_val)
                self.rx_vC.append(vC_val)
                has_new_data = True
            except queue.Empty:
                break

        if has_new_data:
            self.line_iL.set_data(self.rx_time, self.rx_iL)
            self.line_vC.set_data(self.rx_time, self.rx_vC)

            self.rt_ax1.relim()
            self.rt_ax1.autoscale_view()
            self.rt_ax2.relim()
            self.rt_ax2.autoscale_view()

            self.rt_canvas.draw_idle()

        if self.received_count < self.expected_steps and not self.cancel_flag:
            self.root.after(50, self._update_realtime_plot)

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

            # Limite de MAX_MS_LOCAL_SIM ms APENAS na simulação teórica prévia da tela inicial
            plot_sim_time_ms = min(sim_time_ms, float(MAX_MS_LOCAL_SIM))
            time_vec, iL, vC = buck.simulate(N=N, sim_time=plot_sim_time_ms / 1000.0)

            self.ax1.clear()
            self.ax1.plot(time_vec * 1e3, iL, linewidth=1.2, color="tab:blue")
            self.ax1.set_title(f"Corrente no Indutor (Teórico - {'máx 500ms' if sim_time_ms > int(MAX_MS_LOCAL_SIM) else f'{sim_time_ms:.1f}ms'})")
            self.ax1.set_xlabel("Tempo (ms)")
            self.ax1.set_ylabel(r"$i_L$ (A)")
            self.ax1.grid(True, linestyle="--", alpha=0.5)

            self.ax2.clear()
            self.ax2.plot(time_vec * 1e3, vC, linewidth=1.2, color="tab:orange")
            self.ax2.set_title(f"Tensão de Saída (Teórico - {'máx 500ms' if sim_time_ms > int(MAX_MS_LOCAL_SIM) else f'{sim_time_ms:.1f}ms'})")
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
