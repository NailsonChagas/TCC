import customtkinter as ctk

class BuckView(ctk.CTkFrame):
    def __init__(self, master, controller, on_converter_added_callback):
        super().__init__(master)
        self.controller = controller
        self.on_converter_added = on_converter_added_callback
        self.current_mode = "Parâmetros de Projeto"
        
        self.setup_ui()

    def setup_ui(self):
        # Seletor de Modo
        self.mode_selector = ctk.CTkSegmentedButton(
            self, 
            values=["Parâmetros de Projeto", "Componentes do Circuito"],
            command=self.handle_mode_switch
        )
        self.mode_selector.pack(pady=(15, 5))
        self.mode_selector.set("Parâmetros de Projeto")

        # Container Principal
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # ---------------- PAINEL ESQUERDO (Inputs) ----------------
        self.left_panel = ctk.CTkFrame(self.content_frame)
        self.left_panel.pack(side="left", fill="y", padx=(0, 10))

        self.param_entries = {}
        self.comp_entries = {}

        self.setup_parameters_form()
        self.setup_components_form()

        self.save_button = ctk.CTkButton(self.left_panel, text="Salvar Conversor", command=self.handle_save_converter)
        self.save_button.pack(pady=20)

        # ---------------- PAINEL DIREITO (Resultados e Histórico) ----------------
        self.right_panel = ctk.CTkFrame(self.content_frame)
        self.right_panel.pack(side="right", fill="both", expand=True)

        self.result_title = ctk.CTkLabel(self.right_panel, text="Resumo do Dimensionamento", font=("Arial", 14, "bold"))
        self.result_title.pack(pady=(10, 5), padx=15, anchor="w")

        self.result_label = ctk.CTkLabel(self.right_panel, text="Preencha os dados e clique em Salvar.", justify="left")
        self.result_label.pack(pady=5, padx=15, anchor="nw")

        # Separador Visual para a lista em memória
        ctk.CTkLabel(self.right_panel, text="Conversores Salvos em Memória:", font=("Arial", 12, "bold")).pack(pady=(20, 5), padx=15, anchor="w")

        # Frame Rolável para listar o histórico
        self.history_scrollable_frame = ctk.CTkScrollableFrame(self.right_panel, height=150)
        self.history_scrollable_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        self.refresh_converter_history()
        self.handle_mode_switch("Parâmetros de Projeto")

    def create_input_row(self, parent, label_text, row_index):
        ctk.CTkLabel(parent, text=label_text).grid(row=row_index, column=0, padx=10, pady=5, sticky="e")
        entry = ctk.CTkEntry(parent)
        entry.grid(row=row_index, column=1, padx=10, pady=5)
        return entry

    def setup_parameters_form(self):
        self.param_form_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.param_entries['vs'] = self.create_input_row(self.param_form_frame, "Tensão de Entrada - Vs (V):", 0)
        self.param_entries['vo'] = self.create_input_row(self.param_form_frame, "Tensão de Saída - Vo (V):", 1)
        self.param_entries['po'] = self.create_input_row(self.param_form_frame, "Potência - Po (W):", 2)
        self.param_entries['delta_il'] = self.create_input_row(self.param_form_frame, "Ripple de Corrente - ΔiL (A):", 3)
        self.param_entries['delta_vo'] = self.create_input_row(self.param_form_frame, "Ripple de Tensão - ΔVo (V):", 4)
        self.param_entries['fs'] = self.create_input_row(self.param_form_frame, "Freq. Chaveamento - fs (Hz):", 5)
        self.param_entries['fs'].insert(0, "50000")

    def setup_components_form(self):
        self.comp_form_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.comp_entries['vs'] = self.create_input_row(self.comp_form_frame, "Tensão de Entrada - Vs (V):", 0)
        self.comp_entries['vo'] = self.create_input_row(self.comp_form_frame, "Tensão de Saída - Vo (V):", 1)
        self.comp_entries['r'] = self.create_input_row(self.comp_form_frame, "Resistência de Carga - R (Ω):", 2)
        self.comp_entries['l'] = self.create_input_row(self.comp_form_frame, "Indutância - L (H):", 3)
        self.comp_entries['c'] = self.create_input_row(self.comp_form_frame, "Capacitância - C (F):", 4)
        self.comp_entries['fs'] = self.create_input_row(self.comp_form_frame, "Freq. Chaveamento - fs (Hz):", 5)
        self.comp_entries['fs'].insert(0, "50000")

    def handle_mode_switch(self, selected_mode):
        self.current_mode = selected_mode
        self.param_form_frame.pack_forget()
        self.comp_form_frame.pack_forget()

        if selected_mode == "Parâmetros de Projeto":
            self.param_form_frame.pack(pady=10, padx=10)
        else:
            self.comp_form_frame.pack(pady=10, padx=10)

    def refresh_converter_history(self):
        # Limpa o frame de histórico antes de redesenhar
        for widget in self.history_scrollable_frame.winfo_children():
            widget.destroy()

        converters = self.controller.get_all_converters()
        if not converters:
            ctk.CTkLabel(self.history_scrollable_frame, text="Nenhum conversor na memória.").pack(anchor="w")
            return

        for uid, buck in converters.items():
            info_text = f"• {uid} -> L: {buck.L:.4e}H | C: {buck.C:.4e}F | R: {buck.R:.2f}Ω"
            ctk.CTkLabel(self.history_scrollable_frame, text=info_text, font=("Consolas", 11)).pack(anchor="w", pady=2)

    def handle_save_converter(self):
        try:
            converter_count = len(self.controller.get_all_converters()) + 1
            if self.current_mode == "Parâmetros de Projeto":
                vs = float(self.param_entries['vs'].get())
                vo = float(self.param_entries['vo'].get())
                po = float(self.param_entries['po'].get())
                delta_il = float(self.param_entries['delta_il'].get())
                delta_vo = float(self.param_entries['delta_vo'].get())
                fs = float(self.param_entries['fs'].get())
                
                uid = f"BuckParam_Vo{vo}V_Po{po}W_#{converter_count}"
                buck, error_msg = self.controller.register_converter_by_parameters(uid, vs, vo, po, delta_il, delta_vo, fs)
            else:
                vs = float(self.comp_entries['vs'].get())
                vo = float(self.comp_entries['vo'].get())
                r = float(self.comp_entries['r'].get())
                l = float(self.comp_entries['l'].get())
                c = float(self.comp_entries['c'].get())
                fs = float(self.comp_entries['fs'].get())
                
                uid = f"BuckComp_Vo{vo}V_R{r}Ω_#{converter_count}"
                buck, error_msg = self.controller.register_converter_by_components(uid, vs, vo, r, l, c, fs)

            if error_msg:
                self.result_label.configure(text=f"Erro de Validação (CCMError):\n\n{error_msg}", text_color="#ff4a4a")
            else:
                success_msg = (
                    f"Sucesso! Salvo na Memória RAM.\n"
                    f"Razão Cíclica (D): {buck.D:.2f} | R: {buck.R:.2f} Ω\n"
                    f"L: {buck.L:.6e} H (Mín: {buck.Lmin:.6e} H)"
                )
                self.result_label.configure(text=success_msg, text_color="#2dc937")
                self.refresh_converter_history()
                self.on_converter_added()

        except ValueError:
            self.result_label.configure(text="Erro: Preencha todos os campos com valores numéricos.", text_color="#ff4a4a")