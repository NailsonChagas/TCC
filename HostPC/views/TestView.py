import customtkinter as ctk

class TestView(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller
        
        self.setup_ui()

    def setup_ui(self):
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # ---------------- PAINEL ESQUERDO (Formulário do Teste) ----------------
        self.left_panel = ctk.CTkFrame(self.content_frame)
        self.left_panel.pack(side="left", fill="y", padx=(0, 10))

        ctk.CTkLabel(self.left_panel, text="Nova Perturbação (HIL)", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        ctk.CTkLabel(self.left_panel, text="Selecionar Buck:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.converter_combobox = ctk.CTkComboBox(self.left_panel, values=["Nenhum conversor cadastrado"], command=self.handle_converter_selection_change)
        self.converter_combobox.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(self.left_panel, text="Amplitude (V):").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.amplitude_entry = ctk.CTkEntry(self.left_panel)
        self.amplitude_entry.grid(row=2, column=1, padx=10, pady=5)
        self.amplitude_entry.insert(0, "1.0")

        ctk.CTkLabel(self.left_panel, text="Frequência (Hz):").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.frequency_entry = ctk.CTkEntry(self.left_panel)
        self.frequency_entry.grid(row=3, column=1, padx=10, pady=5)
        self.frequency_entry.insert(0, "60")

        self.add_test_button = ctk.CTkButton(self.left_panel, text="Criar e Vincular Teste", command=self.handle_create_test)
        self.add_test_button.grid(row=4, column=0, columnspan=2, pady=15)

        # ---------------- PAINEL DIREITO (Histórico de Testes Vinculados) ----------------
        self.right_panel = ctk.CTkFrame(self.content_frame)
        self.right_panel.pack(side="right", fill="both", expand=True)

        self.test_title_label = ctk.CTkLabel(self.right_panel, text="Testes Vinculados ao Conversor", font=("Arial", 14, "bold"))
        self.test_title_label.pack(pady=(10, 5), padx=15, anchor="w")

        self.test_scrollable_frame = ctk.CTkScrollableFrame(self.right_panel)
        self.test_scrollable_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.refresh_test_history()

    def refresh_converter_list(self):
        converter_uids = list(self.controller.get_all_converters().keys())
        if converter_uids:
            self.converter_combobox.configure(values=converter_uids)
            # Mantém a seleção se ela ainda existir no disco, senão foca no último
            current_selection = self.converter_combobox.get()
            if current_selection not in converter_uids:
                self.converter_combobox.set(converter_uids[-1])
        else:
            self.converter_combobox.configure(values=["Nenhum conversor cadastrado"])
            self.converter_combobox.set("Nenhum conversor cadastrado")
            
        self.refresh_test_history()

    def handle_converter_selection_change(self, choice):
        self.refresh_test_history()

    def refresh_test_history(self):
        # Limpa o histórico visual de testes
        for widget in self.test_scrollable_frame.winfo_children():
            widget.destroy()

        selected_converter = self.converter_combobox.get()
        if selected_converter == "Nenhum conversor cadastrado" or not selected_converter:
            ctk.CTkLabel(self.test_scrollable_frame, text="Selecione um conversor válido para ver seus testes.").pack(anchor="w", padx=5)
            return

        tests = self.controller.get_tests_by_converter(selected_converter)
        self.test_title_label.configure(text=f"Testes Vinculados a [{selected_converter}]")

        if not tests:
            ctk.CTkLabel(self.test_scrollable_frame, text="Nenhum cenário de teste criado para este Buck.").pack(anchor="w", padx=5)
            return

        for index, test in enumerate(tests, start=1):
            info_text = f"Teste #{index} -> Amp: {test.Vs_amplitude}V | Freq: {test.Vs_frequency}Hz | Phase Inc: {test.phase_increment:.4f}"
            ctk.CTkLabel(self.test_scrollable_frame, text=info_text, font=("Consolas", 11)).pack(anchor="w", pady=2, padx=5)

    def handle_create_test(self):
        converter_uid = self.converter_combobox.get()
        if converter_uid == "Nenhum conversor cadastrado" or not converter_uid:
            return

        try:
            amplitude = float(self.amplitude_entry.get())
            frequency = float(self.frequency_entry.get())

            new_test, error_msg = self.controller.add_test_to_converter(converter_uid, amplitude, frequency)

            if not error_msg:
                self.refresh_test_history()
        except ValueError:
            pass