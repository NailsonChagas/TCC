import customtkinter as ctk
from views.BuckView import BuckView
from views.TestView import TestView

class MainWindow(ctk.CTk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        self.title("Plataforma de Dimensionamento de Conversores")
        self.geometry("950x550")
        
        self.setup_tabs()

    def setup_tabs(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)
        
        self.tab_buck = self.tabview.add("Projetar Conversor")
        self.tab_test = self.tabview.add("Configurar Testes")
        
        # Inicializa a visualização do Buck
        self.buck_view = BuckView(
            master=self.tab_buck, 
            controller=self.controller, 
            on_converter_added_callback=self.on_converter_added
        )
        self.buck_view.pack(fill="both", expand=True)
        
        # Inicializa a visualização de Testes
        self.test_view = TestView(
            master=self.tab_test, 
            controller=self.controller
        )
        self.test_view.pack(fill="both", expand=True)

        # CORREÇÃO CRÍTICA: Força o preenchimento da lista de testes na inicialização
        self.test_view.refresh_converter_list()

    def on_converter_added(self):
        # Callback para atualizar quando um conversor novo for criado em tempo de execução
        self.test_view.refresh_converter_list()