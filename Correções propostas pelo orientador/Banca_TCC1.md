# Sugestões passadas durante a banca de TCC 1

Passando a limpo as anotações feitas durante a banca.

## Observações gerais

Os três professores consideraram que o Capítulo 1 está um pouco repetitivo. Foi sugerido juntar mais os tópicos em vez de seguir rigidamente o template.

A banca final deverá ocorrer aproximadamente em **novembro**, com a entrega da versão final em **dezembro**. A versão destinada à banca deverá ser entregue cerca de **uma semana antes da apresentação**.

---

# Minhas anotações

## Prof. Dernadin (Gustavo)

Os questionamentos foram principalmente relacionados à escolha do microcontrolador e das ferramentas de desenvolvimento.

### Arquitetura e processamento

* Avaliar a necessidade de utilizar ponto flutuante de:

  * precisão simples (single precision);
  * precisão dupla (double precision).

  Verificar como essa escolha impacta o desempenho do sistema.

* Avaliar outras famílias STM32. Caso seja necessária precisão dupla, considerar:

  * ARM M7 (STM32H769);
  * ARM M7 (STM32H767);
  * ARM M55;
  * ARM M65.

### Sistema operacional

* Avaliar se realmente é necessário utilizar o FreeRTOS.
* Considerar uma implementação mais sequencial utilizando apenas:

  * interrupções;
  * DMA.

### Comunicação

* Definir como será feita a comunicação entre o microcontrolador e o computador.
* Foi recomendada a utilização da classe **USB CDC**.
* Definir o protocolo de comunicação, ou seja, como os dados serão enquadrados e transferidos.

### Sincronização

* Garantir que a base de tempo do simulador e do controlador estejam sincronizadas.
* Sugestão: utilizar uma interrupção de borda para sincronizar os dispositivos.

---

## Prof. Juliano

Os questionamentos foram principalmente relacionados à modelagem do conversor Buck.

### Modelagem e operação

* Verificar se há conhecimento prévio suficiente sobre o assunto.
* Avaliar se a fonte de entrada será apenas contínua ou se haverá uma componente variável (por exemplo, uma senoide em série), permitindo representar os efeitos da retificação.
* Definir o modo de operação do conversor:

  * contínuo (CCM);
  * descontínuo (DCM).

  Tanto Juliano quanto Cardoso recomendaram utilizar **CCM**.

### Cronograma

* Rever o cronograma, pois a etapa de modelagem provavelmente não será tão demorada.
* Confirmar com a Prof.ª Mariza a data de entrega do TCC 2.

### Apoio oferecido

* O professor se colocou à disposição para auxiliar:

  * na modelagem;
  * em assuntos relacionados à eletrônica de potência.

---

## Prof. Cardoso

### Desenvolvimento

* Iniciar pela modelagem do conversor Buck utilizando variáveis de estado.

* Obter as equações de estado para:

  * chave ligada (ON);
  * chave desligada (OFF).

* A partir dessas equações, obter o modelo médio em espaço de estados, que será utilizado para o projeto do controlador.

### Bibliografia recomendada

#### Livros

* **Ivo Barbi**

  * *Modelagem de Conversores CC-CC Empregando Modelo Médio em Espaço de Estados*.

* **Robert W. Erickson**

  * *Fundamentals of Power Electronics*.

* **Daniel W. Hart**

  * *Power Electronics*.

#### Trabalho acadêmico

* **Letícia Ferreti**

  * *Desenvolvimento de Conversor Bidirecional para Gerenciamento da Carga e Descarga de Baterias de Íons de Lítio*.

---

# Anotações feitas pelo Prof. Cardoso durante a banca

## Gustavo

1. Verificar se será necessário utilizar ponto flutuante de precisão simples ou dupla.
2. Definir se a comunicação será feita por USB ou UART.
3. Caso seja utilizado USB, avaliar a utilização da classe CDC.
4. Sincronizar ADCs e PWMs, provavelmente utilizando uma trigger de borda digital.
5. Incluir um barramento CC + CA, definindo parâmetros de frequência e tensão da componente CA.
6. Definir o protocolo de comunicação.
7. Avaliar a possibilidade de não utilizar RTOS, economizando processamento e memória.
8. Considerar a utilização do STM32H769.

## Juliano

1. Verificar se será utilizado um barramento CC fixo ou com capacitor.
2. Definir se o conversor operará em modo contínuo (CCM) ou descontínuo (DCM).
3. Definir o método de modelagem e simulação. Foi sugerida a utilização de variáveis de estado com operação em CCM.
4. Ajustar o cronograma para incluir as correções da banca e a preparação para a defesa.
