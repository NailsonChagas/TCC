import serial
import struct
import time

# --- Configurações da Porta Serial ---
PORTA_SERIAL = '/dev/ttyACM0'  # Mude para sua porta (ex: /dev/ttyACM0 no Linux)
BAUD_RATE = 115200     # Para USB CDC o baud rate é figurativo, rodará na vel. da USB FS

# --- Dicionário de Cabeçalhos ---
HEAD_CONFIG         = 0x0001
HEAD_CONFIG_SUCCESS = 0x0002
HEAD_CONFIG_FAIL    = 0x0003
HEAD_DATA           = 0x0004
HEAD_SIM_END        = 0x0005

def main():
    try:
        # Abre a porta serial (timeout de 1 segundo para leituras bloqueantes)
        ser = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=1)
        print(f"[{PORTA_SERIAL}] Porta aberta com sucesso!")
        
        # 1. Preparar o pacote CONFIG
        # Formato little-endian (<), uint16 (H), 9 floats (9f), 2 uint32 (2I) -> Total: 46 bytes
        formato_config = '<H9f2I'

        # Parâmetros fictícios para o teste do conversor Buck
        vO_max = 50.0000
        iL_max = 16.0000
        Ad_00, Ad_01 = 0.999997, -0.000159
        Bd1_0 = 0.008000
        Ad_10, Ad_11 = 0.039872, 0.993617
        Bd1_1 = 0.000160  # (Bd1_1 * Vin já calculado no PC)
        fs = 5000.0 # 50 kHz
        n = 100       # 10 passos por período
        total_steps = 50000000 # Executar 50 passos para teste rápido
        
        # Empacota os dados
        pacote_config = struct.pack(
            formato_config,
            HEAD_CONFIG,
            vO_max, iL_max,
            Ad_00, Ad_01, Bd1_0,
            Ad_10, Ad_11, Bd1_1,
            fs, n, total_steps
        )
        
        print(f"Enviando pacote CONFIG ({len(pacote_config)} bytes)...")
        ser.write(pacote_config)
        ser.flush()
        
        # 2. Loop de Recepção (Ouvindo o Microcontrolador)
        simulacao_rodando = True
        
        while simulacao_rodando:
            # Lê os primeiros 2 bytes (o header)
            header_bytes = ser.read(2)
            if len(header_bytes) < 2:
                continue # Timeout sem dados, tenta ler novamente
                
            # Desempacota o header (little-endian, uint16)
            header = struct.unpack('<H', header_bytes)[0]
            
            if header == HEAD_CONFIG_SUCCESS:
                print("[MCU] -> CONFIG_SUCCESS: Configuração aceita! Simulação iniciada.")
                
            elif header == HEAD_CONFIG_FAIL:
                print("[MCU] -> CONFIG_FAIL: Parâmetros inválidos.")
                break
                
            elif header == HEAD_DATA:
                # O pacote DATA tem 14 bytes (header de 2 + payload de 12)
                # Precisamos ler os 12 bytes restantes
                payload_bytes = ser.read(12)
                if len(payload_bytes) == 12:
                    # uint32 (I), 2 floats (2f)
                    k, iL, vC_val = struct.unpack('<I2f', payload_bytes)
                    print(f"[MCU] -> DATA [Passo {k}]: iL={iL:.4f} A, vC={vC_val:.4f} V")
                else:
                    print("Erro: Pacote DATA incompleto!")
                    
            elif header == HEAD_SIM_END:
                print("[MCU] -> SIMULATION_END: Simulação concluída.")
                simulacao_rodando = False
                
            else:
                print(f"[MCU] -> Header Desconhecido: 0x{header:04X}")
                
    except serial.SerialException as e:
        print(f"Erro na porta serial: {e}")
    except KeyboardInterrupt:
        print("\nMonitoramento cancelado pelo usuário.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Porta serial fechada.")

if __name__ == '__main__':
    main()