# Projeto da maquina de estados 

## 1. Dicionário de cabeçalhos e campos do protocolo binário USB

Cada mensagem é composta por um cabeçalho de 2 bytes (`uint16`), seguido pelos campos de dados definidos para aquele tipo de mensagem. O tamanho de cada campo é determinado pelo seu tipo de dado.

### 1.1. Dicionário de cabeçalhos

| Cabeçalho (hex.) | Identificador | Direção |
|---|---|---|
| `0x0001` | `CONFIG` | PC → MCU |
| `0x0002` | `CONFIG_SUCCESS` | MCU → PC |
| `0x0003` | `CONFIG_FAIL` | MCU → PC |
| `0x0004` | `DATA` | MCU → PC |
| `0x0005` | `SIMULATION_END` | MCU → PC |

### 1.2. Tipos de dados e ordem dos bytes

Convenções utilizadas:

- `float32`: número de ponto flutuante de 32 bits, representado no formato IEEE 754, ocupando 4 bytes.
- `uint32`: inteiro sem sinal de 32 bits, ocupando 4 bytes.
- `uint16`: inteiro sem sinal de 16 bits, ocupando 2 bytes.
- `Offset`: posição inicial do campo em bytes, contada a partir do início do pacote, incluindo o cabeçalho.

**O protocolo utiliza exclusivamente a ordem de bytes *little-endian*.** Portanto, o byte menos significativo de cada campo numérico multibyte é transmitido primeiro. Essa convenção deve ser respeitada tanto pelo firmware do STM32H723 quanto pela aplicação no computador.

Por exemplo, o cabeçalho `0x0001` é transmitido pelos bytes `0x01 0x00`.

### 1.3. Estrutura dos campos por mensagem

#### `CONFIG` — `0x0001`

| Campo | Tipo | Tamanho (bytes) | Offset (bytes) |
|---|---|---:|---:|
| `header` | `uint16` | 2 | 0 |
| `vO_max` | `float32` | 4 | 2 |
| `iL_max` | `float32` | 4 | 6 |
| `Ad_00` | `float32` | 4 | 10 |
| `Ad_01` | `float32` | 4 | 14 |
| `Bd1_0` | `float32` | 4 | 18 |
| `Ad_10` | `float32` | 4 | 22 |
| `Ad_11` | `float32` | 4 | 26 |
| `Bd1_1` | `float32` | 4 | 30 |
| `fs` | `float32` | 4 | 34 |
| `n` | `uint32` | 4 | 38 |
| `total_steps` | `uint32` | 4 | 42 |
| **Total** | | **46** | |

**Observação sobre `Bd1_1`:** esse coeficiente da matriz de entrada discretizada já é transmitido multiplicado pela tensão de entrada do conversor Buck (`Vs`). A multiplicação é realizada previamente no computador, de modo que o microcontrolador possa utilizar diretamente o valor recebido, sem executar essa operação durante a simulação.

#### `CONFIG_SUCCESS` — `0x0002`

| Campo | Tipo | Tamanho (bytes) | Offset (bytes) |
|---|---|---:|---:|
| `header` | `uint16` | 2 | 0 |
| **Total** | | **2** | |

#### `CONFIG_FAIL` — `0x0003`

| Campo | Tipo | Tamanho (bytes) | Offset (bytes) |
|---|---|---:|---:|
| `header` | `uint16` | 2 | 0 |
| **Total** | | **2** | |

#### `DATA` — `0x0004`

| Campo | Tipo | Tamanho (bytes) | Offset (bytes) |
|---|---|---:|---:|
| `header` | `uint16` | 2 | 0 |
| `k` | `uint32` | 4 | 2 |
| `iL` | `float32` | 4 | 6 |
| `vC_val` | `float32` | 4 | 10 |
| **Total** | | **14** | |

#### `SIMULATION_END` — `0x0005`

| Campo | Tipo | Tamanho (bytes) | Offset (bytes) |
|---|---|---:|---:|
| `header` | `uint16` | 2 | 0 |
| **Total** | | **2** | |

### 1.4. Resumo dos tamanhos

| Mensagem | Cabeçalho | Dados | Tamanho total |
|---|---:|---:|---:|
| `CONFIG` | 2 bytes | 44 bytes | **46 bytes** |
| `CONFIG_SUCCESS` | 2 bytes | 0 bytes | **2 bytes** |
| `CONFIG_FAIL` | 2 bytes | 0 bytes | **2 bytes** |
| `DATA` | 2 bytes | 12 bytes | **14 bytes** |
| `SIMULATION_END` | 2 bytes | 0 bytes | **2 bytes** |

## 2. Definições dos parâmetros de simulação

- `Vs`: tensão de entrada do conversor Buck, em volts (V).
- `fs`: frequência de chaveamento do conversor Buck, em hertz (Hz).
- `n`: número de passos de simulação executados por período de chaveamento.
- `k`: índice do passo de simulação, incrementado a cada atualização do modelo do conversor.
- `total_steps`: número total de passos de simulação a serem executados.
- `f_sim`: frequência de atualização do modelo do simulador, calculada por `f_sim = fs * n`.
- `T_sim`: intervalo de tempo entre atualizações consecutivas do modelo, calculado por `T_sim = 1 / f_sim`.

Os coeficientes `Ad_00`, `Ad_01`, `Ad_10` e `Ad_11` representam os elementos da matriz de estados discretizada. Os coeficientes `Bd1_0` e `Bd1_1` representam os elementos associados à entrada do modelo discretizado.

O parâmetro `Bd1_1` já é fornecido multiplicado pela tensão de entrada `Vs`. Portanto, o computador deve realizar essa multiplicação antes de transmitir a configuração, e o firmware deve utilizar diretamente o coeficiente recebido.

Por exemplo, para `fs = 50000 Hz` e `n = 100`:

- Frequência de chaveamento do conversor Buck: `50 kHz`.
- Período de chaveamento: `20 µs`.
- Taxa de atualização do simulador: `5 MHz`.
- Intervalo entre passos de simulação: `200 ns`.

Nesse caso, são executados 100 passos de simulação por período de chaveamento do conversor Buck.

## 3. Máquina de estados com comunicação binária via USB

Cada mensagem transmitida via USB começa com um cabeçalho de 2 bytes (`uint16`), que identifica o tipo de mensagem. Os valores definidos no dicionário de cabeçalhos devem ser compartilhados pelo firmware do microcontrolador e pela aplicação no computador.

O cabeçalho é transmitido primeiro, seguido pelos campos binários definidos para cada tipo de mensagem. Todos os campos numéricos utilizam a ordem de bytes *little-endian*, conforme especificado na Seção 1.2.

A máquina de estados é composta por três estados:

- `AguardandoConfiguracao`
- `ConfigurandoSimulador`
- `ExecutandoSimulacao`

### 3.1. `AguardandoConfiguracao`

- Estado inicial do sistema.
- Único estado em que o microcontrolador recebe mensagens de configuração via USB.
- Aguarda o recebimento de um pacote binário com o cabeçalho `CONFIG` (`0x0001`), seguido pelos parâmetros:
  - `vO_max`: `float32`, valor máximo de tensão de saída representado pelo sinal analógico.
  - `iL_max`: `float32`, valor máximo de corrente no indutor representado pelo sinal analógico.
  - `Ad_00`: `float32`, coeficiente da matriz de estados discretizada.
  - `Ad_01`: `float32`, coeficiente da matriz de estados discretizada.
  - `Bd1_0`: `float32`, coeficiente da matriz de entrada discretizada.
  - `Ad_10`: `float32`, coeficiente da matriz de estados discretizada.
  - `Ad_11`: `float32`, coeficiente da matriz de estados discretizada.
  - `Bd1_1`: `float32`, coeficiente da matriz de entrada discretizada, já multiplicado pela tensão de entrada do conversor Buck (`Vs`). Essa multiplicação é realizada previamente no computador.
  - `fs`: `float32`, frequência de chaveamento do conversor Buck, em hertz.
  - `n`: `uint32`, número de passos de simulação por período de chaveamento.
  - `total_steps`: `uint32`, número total de passos de simulação a serem executados.

- O pacote completo possui 46 bytes, incluindo o cabeçalho.
- Após receber o pacote completo, validar o cabeçalho, o tamanho e os parâmetros recebidos.
- Se o pacote for válido, transicionar para `ConfigurandoSimulador`.
- Caso contrário, permanecer em `AguardandoConfiguracao`.

### 3.2. `ConfigurandoSimulador`

- Extrair os parâmetros do pacote binário recebido.
- Configurar o microcontrolador:
  - **Taxa de atualização da simulação:** `f_sim = fs * n`.
  - **Taxa de leitura do estado da chave (aberta/fechada):** `f_chave = 2 * fs`.
  - **Taxa de atualização da saída da simulação:** `f_saida = 2 * fs`.
  - **Taxa de envio da telemetria via USB:** `f_telemetria = fs`.
  - **Coeficientes da simulação:** `Ad_00`, `Ad_01`, `Bd1_0`, `Ad_10`, `Ad_11` e `Bd1_1`.
  - **Fator de conversão da tensão de saída:** `K_vO = 3.3 / vO_max`.
  - **Fator de conversão da corrente no indutor:** `K_iL = 3.3 / iL_max`.

- O coeficiente `Bd1_1` já é recebido multiplicado pela tensão de entrada do conversor (`Vs`). O firmware deve utilizar diretamente o valor recebido, sem realizar novamente essa multiplicação.
- Configurar os temporizadores e os mecanismos de execução necessários para respeitar as frequências definidas.
- Garantir que a taxa de atualização da simulação seja compatível com a capacidade de processamento do microcontrolador.
- Se a configuração for concluída com sucesso:
  - Enviar um pacote binário com o cabeçalho `CONFIG_SUCCESS` (`0x0002`), sem campos adicionais. O pacote possui 2 bytes.
  - Transicionar para `ExecutandoSimulacao`.
- Se ocorrer uma falha durante a configuração:
  - Enviar um pacote binário com o cabeçalho `CONFIG_FAIL` (`0x0003`), sem campos adicionais. O pacote possui 2 bytes.
  - Transicionar para `AguardandoConfiguracao`.

### 3.3. `ExecutandoSimulacao`

- Enquanto `k < total_steps`:
  - Atualizar os estados do simulador conforme a taxa de atualização configurada, `f_sim = fs * n`.
  - Ler o estado da chave (aberta/fechada) conforme a taxa configurada, `f_chave = 2 * fs`.
  - Atualizar a saída do simulador conforme a taxa configurada, `f_saida = 2 * fs`.
  - Enviar os dados de telemetria via USB de maneira não bloqueante, respeitando a taxa de envio configurada, `f_telemetria = fs`.
  - Incrementar o índice `k` a cada passo de simulação executado.
  - Utilizar diretamente os coeficientes recebidos, incluindo `Bd1_1`, sem multiplicá-lo novamente pela tensão de entrada `Vs`.
  - Cada pacote de telemetria deve conter o cabeçalho `DATA` (`0x0004`), seguido pelos campos:
    - `k`: `uint32`, índice do passo de simulação.
    - `iL`: `float32`, corrente no indutor, em ampères (A).
    - `vC_val`: `float32`, tensão no capacitor, em volts (V).

  - O pacote de telemetria possui 14 bytes, incluindo o cabeçalho.

- Quando `k >= total_steps`:
  - Enviar um pacote binário com o cabeçalho `SIMULATION_END` (`0x0005`), sem campos adicionais. O pacote possui 2 bytes.
  - Transicionar para `AguardandoConfiguracao`.

### 3.4. Resumo das transições de estado

| Estado de origem | Condição | Ação | Estado de destino |
|---|---|---|---|
| `AguardandoConfiguracao` | Pacote `CONFIG` válido | Iniciar configuração | `ConfigurandoSimulador` |
| `AguardandoConfiguracao` | Pacote inválido ou incompleto | Aguardar ou continuar a recepção | `AguardandoConfiguracao` |
| `ConfigurandoSimulador` | Configuração concluída com sucesso | Enviar `CONFIG_SUCCESS` | `ExecutandoSimulacao` |
| `ConfigurandoSimulador` | Falha na configuração | Enviar `CONFIG_FAIL` | `AguardandoConfiguracao` |
| `ExecutandoSimulacao` | `k < total_steps` | Continuar a simulação e transmitir telemetria | `ExecutandoSimulacao` |
| `ExecutandoSimulacao` | `k >= total_steps` | Enviar `SIMULATION_END` | `AguardandoConfiguracao` |

## 4. Observações de implementação

- **Nomenclatura dos estados:** utilizar `AguardandoConfiguracao`, `ConfigurandoSimulador` e `ExecutandoSimulacao` como identificadores da máquina de estados. Os nomes não possuem acentos, facilitando sua utilização no código C.
- **Ordem dos bytes:** o protocolo utiliza exclusivamente *little-endian*. Para campos multibyte, o byte menos significativo é transmitido primeiro. Por exemplo, o cabeçalho `0x0001` é transmitido como `0x01 0x00`.
- **Representação numérica:** os campos `float32` utilizam IEEE 754 de 32 bits, enquanto `uint32` e `uint16` representam inteiros sem sinal de 32 e 16 bits, respectivamente.
- **Serialização:** os offsets apresentados correspondem ao formato serializado do protocolo. Não se deve pressupor que o layout de uma `struct` em C corresponda automaticamente a esses offsets, devido a possíveis regras de alinhamento e preenchimento (*padding*).
- **Recepção dos pacotes:** como os pacotes possuem tamanhos fixos por tipo, o receptor deve identificar a mensagem pelo cabeçalho e receber a quantidade correspondente de bytes antes de processá-la.
- **Pacotes incompletos:** o firmware deve lidar com recepções parciais, pois uma operação de leitura USB não garante que todos os bytes de uma mensagem sejam recebidos de uma só vez.
- **Transmissão não bloqueante:** o envio da telemetria deve ser implementado sem bloquear a execução da simulação, especialmente considerando a taxa de atualização de até 5 MHz.
- **Validação:** os parâmetros de configuração devem ser verificados antes de configurar os temporizadores e iniciar a simulação, incluindo a validade dos valores numéricos, a prevenção de divisões por zero e os limites de frequência suportados pelo hardware.
- **Coeficiente pré-calculado:** `Bd1_1` já inclui a multiplicação pela tensão de entrada `Vs`. Essa operação é realizada no computador antes da transmissão da configuração, evitando uma multiplicação adicional no microcontrolador durante a simulação.