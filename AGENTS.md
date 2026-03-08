# AGENTS.md

## Projeto
PokerTool is a real-time heads-up poker assistant.
The system captures the poker table from the screen, identifies the current game state, and queries previously solved strategies generated with PioSolver.
The goal is to provide strategic suggestions in real time based on solver outputs.

## Main Goals
Priorities for this project:
- High accuracy in table recognition
- Low latency (real-time performance)
- Clean and modular architecture
- Maintainable and extensible codebase

## Language Standard

All development must be done in English. Do not mix Portuguese and English in the codebase.

This includes:
- Source code
- Function names
- Variable names
- File names
- Code comments
- Documentation
- Commit messages

## Tech Stack
- Python 3.13.12
- VSCode
- OpenCV
- OCR for numeric values (bets, stacks, pot)
- PioSolver solved strategy files as the decision engine

## Como rodar
- Always use local .venv

### Windows
Activate venv:
.venv\Scripts\Activate.ps1

Run Project:
python main.py

## Estrutura esperada
- main.py            → Entry point
- capture/           → Screen capture and ROI extraction
- recognition/       → Detection of board, stacks, bets, and positions
- state/             → Game state models and poker domain objects
- solver/            → Lookup and processing of solved PioSolver strategies
- ui/                → Overlay and visual output
- utils/             → Helper utilities
- images/            → Images of static objets used for anchoring

## Architecture Rules
- Do not mix screen capture logic with decision logic.
- OCR and image recognition must stay isolated inside the recognition layer.
- Solver lookup logic must remain inside the solver module.
- Poker decision logic must not be mixed with UI code.
- All table reads must return structured objects representing the game state.

## Implementation Preferences
Prefer:
- Small, focused functions
- Clear and descriptive names
- Modular code
- Explicit data structures
- Type hints where useful
- dataclasses for simple structured data

Avoid:
- Large classes with multiple responsibilities
- Hardcoded values scattered throughout the code
- Complex nested logic
- Premature optimization

## Performance
This project operates in real time. When implementing code:
- Avoid heavy computations inside frame loops
- Avoid repeatedly loading large files
- Prefer caching and indexing strategies
- Minimize disk access during gameplay
- Keep detection pipelines lightweight

## What to Avoid
- Large refactors without clear necessity
- Mixing responsibilities across modules
- Introducing unnecessary dependencies
- Rewriting working code without justification
- Hardcoding UI coordinates without calibration support