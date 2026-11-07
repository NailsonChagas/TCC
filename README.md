# Plataforma HIL para Validação de Controladores Digitais em Conversores Buck

Este repositório contém os arquivos relacionados ao desenvolvimento do **Trabalho de Conclusão de Curso (TCC)** de **Nailson Francisco da Silva Chagas**, cujo objetivo é o desenvolvimento de uma plataforma **Hardware-in-the-Loop (HIL)** para validação de controladores digitais embarcados aplicados a conversores **CC-CC do tipo buck**.

## Sobre o Projeto

O presente trabalho desenvolve uma plataforma de simulação em tempo real (RTDS) utilizando a metodologia *Model-Based Design* (MBD) para interligar a teoria de controle digital, modelagem matemática discreta e eletrônica de potência. A plataforma permite testar e validar controladores digitais físicos em malha fechada de forma segura, emulando o comportamento do conversor buck antes de sua aplicação em um hardware de potência real.

O ecossistema do projeto é dividido em:
* **Emulador da Planta:** Um *firmware* *bare-metal* executado em um microcontrolador STM32, que resolve a modelagem matemática (matrizes em espaço de estados e Transformada de Tustin) da planta em tempo real, garantindo o determinismo na execução.
* **Interface e Telemetria:** Uma interface gráfica desenvolvida em Python (via Tkinter e Matplotlib) que se comunica com o emulador via USB CDC, permitindo a configuração de parâmetros do simulador e a visualização dos dados em tempo real.

## Estrutura do Repositório

O código-fonte e os arquivos desenvolvidos ao longo deste trabalho estão disponibilizados em um repositório público na plataforma GitHub, acessível por meio do endereço:

https://github.com/NailsonChagas/TCC

O repositório está organizado em diferentes diretórios, contendo os códigos-fonte, arquivos de configuração e demais recursos relacionados ao desenvolvimento do trabalho. Entre eles, destacam-se os seguintes diretórios principais:

* **`SimuladorFirmware/`**: contém o projeto do firmware executado pelo microcontrolador responsável pela simulação em tempo real do conversor CC-CC.
* **`BuckInterface/`**: contém os arquivos do projeto da interface gráfica utilizada para configuração dos parâmetros do simulador, inicialização dos experimentos e visualização dos dados de telemetria.
* **`DispositivoVirtual/`**: contém o projeto do dispositivo serial virtual desenvolvido para permitir os testes da interface gráfica durante a etapa de desenvolvimento em que o microcontrolador utilizado no simulador ainda não estava disponível. Esse dispositivo reproduzia a comunicação serial esperada pela interface, permitindo verificar suas funcionalidades sem a necessidade do hardware físico.

O repositório também disponibiliza os demais arquivos e recursos utilizados durante o desenvolvimento e a validação da plataforma HIL, permitindo a consulta e a reprodução das implementações realizadas ao longo deste trabalho.

## Principais Resultados e Conclusões

A validação do projeto demonstrou a viabilidade técnica e a integridade da arquitetura computacional proposta para a plataforma HIL. As principais conclusões obtidas foram:

* **Gerenciamento de Tempo Real:** A avaliação empírica do custo computacional do *solver*, realizada via instrumentação de software (registrador DWT), revelou um consumo médio de 476 ciclos de *clock*. Isso fundamentou a execução segura e estável da simulação em uma frequência de 5 kHz, respeitando estritamente o orçamento de processamento disponível no microcontrolador.
* **Acurácia do Modelo e Estabilidade:** A validação em malha fechada comprovou a robustez da modelagem discreta (Euler, Trapézio e ZOH) e da análise do erro de quantização (DAC). Os testes apresentaram um Erro Absoluto Percentual Médio (MAPE) estático na faixa de 4,55%, indicando alta compatibilidade dos transientes simulados com a teoria.
* **Trabalhos Futuros:** Como perspectiva de evolução, o trabalho sugere a migração do processamento do *solver* para um FPGA e a delegação do controle de E/S analógica via DMA, o que permitiria operar a plataforma em frequências de comutação ainda mais elevadas, alinhando-se aos simuladores HIL comerciais de alto desempenho.

## Cronograma do Projeto

| Atividades                             | Mar | Abr | Mai | Jun | Jul | Ago | Set | Out | Nov | Dez |
| -------------------------------------- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Revisão bibliográfica                  | x   | x   | x   |     |     |     |     |     |     |     |
| Modelagem matemática do conversor buck |     |     | x   |     |     |     |     |     |     |     |
| Discretização do modelo                |     |     | x   |     |     |     |     |     |     |     |
| Definição da arquitetura HIL           |     |     | x   | x   |     |     |     |     |     |     |
| Implementação do firmware embarcado    |     |     |     | x   | x   |     |     |     |     |     |
| Integração da plataforma HIL           |     |     |     |     | x   | x   | x   |     |     |     |
| Testes experimentais e validação       |     |     |     |     |     |     | x   | x   | x   |     |
| Redação do TCC                         | x   | x   | x   | x   | x   | x   | x   | x   | x   | x   |

## Referências

- [A Model-Based Design and Verification Framework for Virtual ECUs in Automotive Seat Control Systems](https://www.mdpi.com/2079-9292/15/3/569)
- [A Rapid Review on Advanced Software-in-the-Loop Methods for Automotive Software Verification](https://sol.sbc.org.br/index.php/sast/article/view/30216)
- [Aplicação do Modelo Linear de Vorpérian ao Conversor tipo Buck](https://www.eletrica.ufpr.br/mehl/downloads/modelamento-buck.pdf)
- [Computer Organization and Embedded Systems](https://www.amazon.com/Computer-Organization-Professor-Electrical-Engineering/dp/0073380652)
- [Consistent Test Reuse Across MIL → SIL → HIL in a Model-Driven Development Workflow (Siemens)](https://www.plm.automation.siemens.com/media/global/cz/Siemens-SW-Consistent-test-reuse-across-MIL-White-Paper_tcm84-98441.pdf)
- [Cost-effective and versatile Hardware-in-the-Loop system for DC/DC converter emulation in education and research](https://www.hardware-x.com/article/S2468-0672(25)00079-3/fulltext)
- [Controle Digital Aplicado](https://www.amazon.com.br/Controle-Digital-Aplicado-Augusto-Ang%C3%A9lico/dp/6555063637)
- [ELETRÔNICA de POTÊNCIA: Dispositivos, circuitos e aplicações](https://www.amazon.com.br/Eletr%C3%B4nica-pot%C3%AAncia-dispositivos-circuitos-aplica%C3%A7%C3%B5es/dp/8543005949)
- [Hardware Emulation of Step-Down Converter Power Stages for Digital Control Design ](https://www.mdpi.com/2079-9292/12/6/1328)
- [Hardware in the Loop Real-time Simulation for the Associated Discrete Circuit Modeling Optimization Method of Power Converters](https://www.mdpi.com/1996-1073/11/11/3237)
- [Hardware-in-the-loop simulation for the design and testing of engine-control systems](https://www.sciencedirect.com/science/article/abs/pii/S0967066198002056)
- [Hardware-in-the-Loop Simulations: A Historical Overview of Engineering Challenges](https://www.mdpi.com/2079-9292/11/15/2462)
- [Model-Based System Design for MIL, SIL, and HIL](https://www.mdpi.com/2032-6653/5/4/1121)
- [Model-Driven Engineering in Education](https://ieeexplore.ieee.org/document/8624724)
- [Modelling and Control of a Buck Converter Using State-Space Averaging and Classical Feedback Techniques](https://arxiv.org/abs/2507.09115)
- [Modern Control Engineering - 5th Edition](https://www.amazon.com.br/Modern-Control-Engineering-Fifth-English-ebook/dp/B08P5ZRZXN)
- [Power Electronics](https://www.amazon.com.br/Power-Electronics-Daniel-Hart-Professor/dp/0073380679)
- [Real-Time Hardware-In-The-Loop (HIL) Testing for Power Electronics Controllers](https://ieeexplore.ieee.org/document/6307219)
- [Sistemas Operacionais de Tempo Real e sua Aplicação em Sistemas Embarcados](https://www.amazon.com.br/Sistemas-Operacionais-Tempo-Aplica%C3%A7%C3%A3o-Embarcados/dp/8521213964)
- [State space averaging technique of power converter with digital PID controller](https://ieeexplore.ieee.org/document/5395907)
- [Testing Embedded Software: A Survey of the Literature](https://www.sciencedirect.com/science/article/pii/S0950584918301265)
- [X-in-the-Loop Methodology for Proton Exchange Membrane Fuel Cell Systems Design: Review of Advances and Challenges](https://www.mdpi.com/1996-1073/18/14/3774)
