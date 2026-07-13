import customtkinter as ctk

class TestView(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller
        
        # Variáveis de estado na memória local da View
        self.selected_converter = None
        self.converter_buttons = {}  # Dicionário para gerir o estado dos botões da lista
        
        self.setup_ui()

    def setup_ui(self):
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # ---------------- PAINEL ESQUERDO (Formulário do Teste) ----------------
        self.left_panel = ctk.CTkFrame(self.content_frame)
        self.left_panel.pack(side="left", fill="y", padx=(0, 10))

        ctk.CTkLabel(self.left_panel, text="Nova Perturbação (HIL)", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=10)

        # Label da lista de seleção
        ctk.CTkLabel(self.left_panel, text="Selecionar Buck:").grid(row=1, column=0, padx=10, pady=5, sticky="ne")
        
        # SOLUÇÃO NATIVA: Um Frame rolável interno para listar os conversores salvos
        self.selection_frame = ctk.CTkScrollableFrame(self.left_panel, height=120, width=160)
        self.selection_frame.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

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

        # Label de Erro
        self.error_label = ctk.CTkLabel(self.right_panel, text="", text_color="#ff4a4a")
        self.error_label.pack(pady=0, padx=15, anchor="w")

        self.test_scrollable_frame = ctk.CTkScrollableFrame(self.right_panel)
        self.test_scrollable_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.refresh_test_history()

    def refresh_converter_list(self):
        """Atualiza a lista interna de conversores desenhando botões clicáveis."""
        # Limpa todos os widgets de seleção antigos
        for widget in self.selection_frame.winfo_children():
            widget.destroy()
        self.converter_buttons.clear()

        converter_uids = list(self.controller.get_all_converters().keys())
        
        if not converter_uids:
            label = ctk.CTkLabel(self.selection_frame, text="Nenhum cadastrado", font=("Arial", 11, "italic"))
            label.pack(pady=10)
            self.selected_converter = None
        else:
            # Se o conversor selecionado anteriormente desapareceu, foca no mais recente
            if self.selected_converter not in converter_uids:
                self.selected_converter = converter_uids[-1]

            # Reconstrói os botões para cada conversor ativo
            for uid in converter_uids:
                is_selected = (uid == self.selected_converter)
                bg_color = "#1f538d" if is_selected else "#343638"
                hover_color = "#14375e" if is_selected else "#565b5e"
                
                # Criamos um mini-botão plano para cada conversor da lista
                btn = ctk.CTkButton(
                    self.selection_frame,
                    text=uid,
                    fg_color=bg_color,
                    hover_color=hover_color,
                    height=24,
                    font=("Arial", 11),
                    command=lambda u=uid: self.select_converter(u)
                )
                btn.pack(fill="x", pady=2, padx=2)
                self.converter_buttons[uid] = btn
                
        self.refresh_test_history()

    def select_converter(self, uid):
        """Método chamado ao clicar num conversor da lista interna."""
        self.selected_converter = uid
        self.error_label.configure(text="")
        
        # Atualiza as cores dos botões para refletir a seleção ativa
        for name, btn in self.converter_buttons.items():
            if name == uid:
                btn.configure(fg_color="#1f538d", hover_color="#14375e")
            else:
                btn.configure(fg_color="#343638", hover_color="#565b5e")
                
        self.refresh_test_history()

    def refresh_test_history(self):
        """Atualiza a tabela de testes vinculada ao conversor atualmente destacado."""
        for widget in self.test_scrollable_frame.winfo_children():
            widget.destroy()

        selected_converter = self.selected_converter
        if not selected_converter:
            self.test_title_label.configure(text="Testes Vinculados ao Conversor")
            ctk.CTkLabel(self.test_scrollable_frame, text="Cadastre um conversor na aba ao lado.").pack(anchor="w", padx=5)
            return

        tests = self.controller.get_tests_by_converter(selected_converter)
        self.test_title_label.configure(text=f"Testes Vinculados a [{selected_converter}]")

        if not tests:
            ctk.CTkLabel(self.test_scrollable_frame, text="Nenhum cenário de teste criado para este Buck.").pack(anchor="w", padx=5)
            return

        for index, test in enumerate(tests, start=1):
            info_text = f"Teste #{index} -> Amp: {test.Vs_amplitude}V | Freq: {test.Vs_frequency}Hz | Phase Inc: {test.phase_increment:.4f}"
            ctk.CTkLabel(self.test_scrollable_frame, text=info_text, font=("Consolas", 11)).pack(anchor="w", pady=2, padx=5)

        self.update_idletasks()

    def handle_create_test(self):
        self.error_label.configure(text="") 
        selected_converter = self.selected_converter
        
        if not selected_converter:
            self.error_label.configure(text="Aviso: Selecione um conversor na lista primeiro.")
            return

        try:
            amp_str = self.amplitude_entry.get().replace(",", ".")
            freq_str = self.frequency_entry.get().replace(",", ".")

            amplitude = float(amp_str)
            frequency = float(freq_str)

            new_test, error_msg = self.controller.add_test_to_converter(selected_converter, amplitude, frequency)

            if not error_msg:
                self.refresh_test_history()
            else:
                self.error_label.configure(text=f"Erro interno: {error_msg}")
                
        except ValueError:
            self.error_label.configure(text="Erro: Insira valores numéricos (ex: 1.5).")