# AGENTS.md

## Projeto
PokerTool é um assistente de poker online em tempo real.
O sistema captura a mesa, identifica o estado da mão e consulta soluções previamente geradas no PioSolver.

## Objetivo principal
Priorizar:
1. precisão na leitura da mesa
2. latência baixa
3. código simples e modular
4. facilidade de manutenção

## Stack
- Python 3.13.12
- VSCode
- OpenCV
- OCR para números/textos da mesa
- arquivos solvados do PioSolver como fonte de decisão

## Como rodar
Use sempre o ambiente virtual local do projeto.

### Windows
Ativar venv:
.venv\Scripts\Activate.ps1

Rodar:
python main.py

## Estrutura esperada
<!-- - `main.py`: ponto de entrada
- `capture/`: captura da tela e ROIs
- `recognition/`: leitura de board, stacks, bets e posição
- `domain/`: modelos de estado da mão
- `solver/`: lookup dos arquivos solvados
- `ui/`: overlay e saída visual -->

## Regras de arquitetura
- Não misturar captura de tela com lógica de decisão.
- Não colocar regra de solver dentro de arquivos de OCR.
- Toda leitura da mesa deve retornar um objeto estruturado.
- Toda consulta ao solver deve passar por uma camada de normalização de spot.

## Preferências de implementação
- Preferir funções pequenas e legíveis.
- Evitar classes grandes com múltiplas responsabilidades.
- Evitar dependências desnecessárias.
- Sempre que possível, separar código determinístico de código probabilístico.
- Para cartas e elementos fixos da mesa, preferir template matching em vez de OCR genérico.
- Para números variáveis como stack, pot e bet, OCR é permitido.

## Performance
Este projeto é sensível a latência.
Ao sugerir código:
- evitar loops desnecessários em tempo real
- evitar recarregar arquivos grandes a cada frame
- preferir cache e indexação
- pensar em lookup rápido para boards e spots

## Convenções
- nomes de arquivos em snake_case
- nomes de funções descritivos
- usar type hints quando fizer sentido
- usar dataclasses para estados simples

## Antes de editar código
Sempre entender:
1. de onde vem a imagem
2. qual ROI está sendo usada
3. qual estrutura representa o game state
4. como o spot será mapeado para a solução do solver

## O que evitar
- mudanças grandes sem necessidade
- refatorações amplas sem preservar comportamento
- hardcode espalhado pelo projeto
- lógica de poker misturada com lógica de interface

## Saída esperada das mudanças
Ao propor alterações:
- explicar brevemente o motivo
- preservar compatibilidade com o fluxo atual
- sugerir código incremental, não reescrita total