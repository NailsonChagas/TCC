import json
import os
from models.BuckConverterCCM import BuckConverterCCM, CCMError
from models.SimulatorTest import SimulatorTest

class AppController:
    def __init__(self, filename="data.json"):
        self.filename = filename
        self.converters = {}  # Memória em runtime
        self.tests = {}       # Memória em runtime
        
        # Carrega os dados salvos em disco na inicialização do app
        self.load_from_disk()

    def save_to_disk(self):
        """Salva o estado atual dos conversores e testes em um arquivo JSON."""
        data = {
            "converters": {},
            "tests": {}
        }
        
        # Serializa os Conversores (parâmetros de hardware)
        for uid, buck in self.converters.items():
            data["converters"][uid] = {
                "Vs": buck.Vs,
                "Vo": buck.Vo,
                "R": buck.R,
                "L": buck.L,
                "C": buck.C,
                "fs": buck.fs
            }
            
        # Serializa os Testes vinculados a cada conversor
        for uid, test_list in self.tests.items():
            data["tests"][uid] = []
            for test in test_list:
                data["tests"][uid].append({
                    "amplitude": test.Vs_amplitude,
                    "frequency": test.Vs_frequency
                })
                
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Erro ao salvar dados no disco: {e}")

    def load_from_disk(self):
        """Lê o arquivo JSON e reconstrói de forma segura os objetos em memória."""
        if not os.path.exists(self.filename):
            return
            
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # 1. Reconstrói os conversores com tratamento de erro isolado
            converters_data = data.get("converters", {})
            for uid, info in converters_data.items():
                try:
                    buck = BuckConverterCCM.from_circuit_components(
                        Vs=float(info["Vs"]),
                        Vo=float(info["Vo"]),
                        R=float(info["R"]),
                        L=float(info["L"]),
                        C=float(info["C"]),
                        fs=float(info["fs"])
                    )
                    self.converters[uid] = buck
                    self.tests[uid] = []
                except CCMError as e:
                    print(f"Aviso: Conversor '{uid}' ignorado ao carregar (condição CCM violada): {e}")
                except Exception as e:
                    print(f"Aviso: Erro ao carregar o conversor '{uid}': {e}")
                
            # 2. Reconstrói e vincula os testes aos conversores ativos
            tests_data = data.get("tests", {})
            for uid, test_list in tests_data.items():
                if uid in self.converters:
                    buck = self.converters[uid]
                    for t_info in test_list:
                        try:
                            test_obj = SimulatorTest(
                                converter=buck,
                                amplitude=float(t_info["amplitude"]),
                                frequency=float(t_info["frequency"])
                            )
                            self.tests[uid].append(test_obj)
                        except Exception as e:
                            print(f"Aviso: Erro ao reconstruir teste do conversor '{uid}': {e}")
                            
        except Exception as e:
            print(f"Erro crítico ao ler o arquivo de persistência: {e}")

    def register_converter_by_parameters(self, uid, vs, vo, po, delta_il, delta_vo, fs):
        try:
            buck = BuckConverterCCM.from_design_parameters(vs, vo, po, delta_il, delta_vo, fs)
            self.converters[uid] = buck
            if uid not in self.tests:
                self.tests[uid] = []
            self.save_to_disk()
            return buck, None
        except CCMError as e:
            return None, str(e)

    def register_converter_by_components(self, uid, vs, vo, r, l, c, fs):
        try:
            buck = BuckConverterCCM.from_circuit_components(vs, vo, r, l, c, fs)
            self.converters[uid] = buck
            if uid not in self.tests:
                self.tests[uid] = []
            self.save_to_disk()
            return buck, None
        except CCMError as e:
            return None, str(e)

    def add_test_to_converter(self, converter_uid, amplitude, frequency):
        if converter_uid not in self.converters:
            return None, "Conversor não encontrado."
        
        buck = self.converters[converter_uid]
        new_test = SimulatorTest(converter=buck, amplitude=amplitude, frequency=frequency)
        self.tests[converter_uid].append(new_test)
        self.save_to_disk()
        return new_test, None

    def get_all_converters(self):
        return self.converters

    def get_tests_by_converter(self, converter_uid):
        return self.tests.get(converter_uid, [])