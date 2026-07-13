import customtkinter as ctk
from views.BuckView import BuckView
from views.TestView import TestView

class MainWindow(ctk.CTk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        self.title("Plataforma de Dimensionamento de Conversores")
        
        # 1. Define o tamanho padrão de abertura (um pouco maior para dar respiro)
        self.geometry("1100x800")
        
        # 2. GARANTIA CRÍTICA: Impede que a janela seja reduzida a ponto de cortar os itens
        self.minsize(1050, 700)
        
        # 3. Permite que a janela seja maximizada e redimensionada livremente
        self.resizable(True, True)
        
        self.setup_tabs()

    def setup_tabs(self):
        # O CTkTabview deve preencher todo o espaço disponível da janela principal
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)
        
        self.tab_buck = self.tabview.add("Adicionar Conversor")
        self.tab_test = self.tabview.add("Configurar Testes")
        
        # As Views internas DEVEM usar fill="both" e expand=True para acompanhar o redimensionamento
        self.buck_view = BuckView(
            master=self.tab_buck, 
            controller=self.controller, 
            on_converter_added_callback=self.on_converter_added
        )
        self.buck_view.pack(fill="both", expand=True)
        
        self.test_view = TestView(
            master=self.tab_test, 
            controller=self.controller
        )
        self.test_view.pack(fill="both", expand=True)

        # Força o carregamento inicial dos conversores salvos em disco (.json)
        self.test_view.refresh_converter_list()

    def on_converter_added(self):
        # Callback síncrono para atualizar a lista na aba de testes
        self.test_view.refresh_converter_list()