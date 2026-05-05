# Anotações sobre como escrever a revisão bibliográfica

Um exemplo de TCC que o prof Cardoso passou: [Implementação de um conversor boost para sistema fotovoltaico](https://repositorio.utfpr.edu.br/jspui/handle/1/40194)

## Como escrever a parte necessária para o TCC 1

1. Separar os trabalhos que selecionei em categorias:
   - X-in-the-loop
   - Embarcados
   - Eletrônica de Potência
   - Teoria de controle

2. Escrever a revisão bibliográfica baseado nos trabalhos da categoria X-in-the-loop:
   - O que é X-in-the-loop? → Contextualizar para eletrônica de potência
   - O que é o HIL e por que ele é importante? → Contextualizar para eletrônica de potência

3. Escrever a metodologia e anexos usando os trabalhos nas categorias Eletrônica de Potência, Teoria de controle e Embarcados:
   - Metodologia: discretização da planta e implementação em microcontrolador
   - Anexos:
     - Projeto de conversor buck
     - Discretização de controlador PID

## Nova estrutura do trabalho

0. Resumo
1. Introdução
   1. Contextualização
   2. Objetivos
      1. Objetivo geral
      2. Objetivos específicos
   3. Justificativa
   4. Estrutura do trabalho

2. Revisão Bibliográfica
   1. Desenvolvimento Baseado em Modelos e o Ciclo em V
   2. As abordagens X-in-the-Loop (XIL)
      - Brevemente definir os tipos de X-in-the-Loop e contextualizar seus usos para eletrônica de potência:
        - MIL
        - SIL
        - ...
        - HIL → apenas dizer que existe; terá um tópico só dele
   3. Simulação Hardware-in-the-Loop (HIL)
      - Sua definição
      - Onde e como surgiu
      - Para que serve e suas vantagens e desvantagens (contextualizar para eletrônica de potência)
      - Falar sobre plataformas comerciais e seus custos
      - Falar que trabalhos recentes estão explorando a criação de plataformas HIL modulares e de baixo custo baseadas em microcontroladores acessíveis

3. Modelagem e Desenvolvimento do Sistema
    1. Materiais a serem usados
    2. Modelagem do sistema
    3. Desenvolvimento do Sistema → ***Não abordado em TCC 1, fazer no TCC 2***

4. Resultados → ***Não abordado em TCC 1, fazer no TCC 2***

5. Conclusão → ***Não abordado em TCC 1, fazer no TCC 2***

6. Referências

7. Anexos
   1. Projeto de conversores Buck projetados para operar em CCM
   2. Discretização e implementação de controladores PID

## Uso de LLM no TCC

Em relação ao uso de ferramentas de LLM para auxiliar a escrita do trabalho:

[**PORTARIA CNPq**](http://memoria2.cnpq.br/web/guest/view/-/journal_content/56_INSTANCE_0oED/10157/23142775) ***Nº 2.664, Artigo 9, Inciso I, alínea* C**: declarar o uso de ferramentas de Inteligência Artificial Generativa (IAG), de qualquer espécie e em qualquer fase do desenvolvimento da pesquisa (concepção, redação, análise de dados, submissão), especificando nos respectivos textos e exposições eletrônicas a ferramenta utilizada e a finalidade.

## Metas
1. **Terminar uma primeira versão da monografia de TCC 1** até o dia **11/05/2026** e enviar para o Cardoso fazer correções

2. **Fazer as correções** até o dia **18/05/2026** e enviar para o Cardoso para checar se está bom o bastante para a banca de TCC 1