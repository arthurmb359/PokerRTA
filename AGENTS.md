# AGENTS.md

## Project

PokerRTA is a real-time heads-up poker assistant.

The system captures the poker table from the screen, identifies the current game state, and queries previously solved strategies generated with PioSolver.

The goal is to provide strategic suggestions in real time based on solver outputs.

---

# Main Goals

Priorities for this project:

- High accuracy in table recognition
- Low latency (real-time performance)
- Clean and modular architecture
- Maintainable and extensible codebase

---

# Language Standard

All development must be done in **English**.  
Do not mix Portuguese and English in the codebase.

This includes:

- Source code
- Function names
- Variable names
- File names
- Code comments
- Documentation
- Commit messages

---

## Change Application Rules

When modifying code, always prefer editor-applied, reviewable changes.

Rules:
- Always make small, incremental changes.
- Prefer the smallest possible diff.
- Do not perform large rewrites in one step.
- Do not mix file moves, renames, deletes, and logic refactors in the same step.
- Keep changes easy to review in the VSCode review pane.
- Avoid aggressive terminal-based bulk rewrites when a normal code edit is sufficient.
- Preserve Git-reviewable changes whenever possible.
- After each task, summarize modified files and expected manual tests.

---

# Tech Stack

- Python 3.13.12
- VSCode
- OpenCV
- OCR for numeric values (bets, stacks, pot)
- PioSolver solved strategy files as the decision engine

---

# How to run

Always use the local `.venv`.

### Windows
Activate venv: .venv\Scripts\Activate.ps1
Run project: python main.py

---

# System Pipeline

The project follows a strict data-processing pipeline:
Screen -> capture -> table -> recognition -> domain (GameState) -> solver -> ui

Each layer has a clear responsibility and must not mix concerns.

---

# Code Structure

main.py → Entry point
controllers/ → Application flow and session orchestration
domain/ → Poker domain models and game state objects
services/ → Operational services
capture/ → Screen capture
table/ → Table geometry, anchors, calibration, region mapping
recognition/ → Detection and reading of bets, board, stacks, positions
solver/ → Solver lookup and strategy processing
ui/ → Overlay and visual output
configs/ → App settings and calibration data
assets/images/ → Static images, anchors, templates
utils/ → Small generic helpers only
tests/ → Automated tests


---

# Layer Responsibilities

## main.py

Entry point of the application.

Responsibilities:

- Start the application
- Initialize controllers
- Launch the main loop

No business logic should live here.

---

# controllers/

Controllers orchestrate the application.

Responsibilities:

- Start and stop game sessions
- Handle navigation between UI states
- Manage session lifecycle
- Connect UI with services

Controllers must not perform OCR or table recognition directly.


---

# domain/

The domain layer defines poker concepts and structured state.
Rules:

- Domain models must be **pure data structures**
- No OCR
- No UI logic
- No screen capture
- No solver file parsing

---

# services/

Services perform operational work.

Each submodule has a strict responsibility.

---

# services/capture/

Responsible for **capturing pixels from the screen**.

Responsibilities:

- Capture full screen
- Capture screen regions
- Manage multi-monitor setups
- Provide raw image frames

Important rule: capture returns **raw images only**.
It must not interpret table content.

---

# services/table/

Responsible for understanding **table geometry and layout**.

Responsibilities:

- Detect table anchor
- Locate the table on screen
- Compute table bounding box
- Convert relative coordinates into absolute regions
- Manage calibration
- Provide table layout information


### Scraper vs Analyzer

**TableScraper**

Responsible for extracting raw visual regions from the table.

Examples:

- locating the table
- cropping regions
- retrieving screenshots
- mapping region coordinates

It deals only with **pixels and geometry**.

**TableAnalyzer**

Responsible for coordinating table reading.

Examples:

- collecting regions from the scraper
- calling recognition services
- building a structured GameState snapshot

It does **not perform UI logic or solver queries**.

---

# services/recognition/

Responsible for interpreting pixels inside table regions.

Responsibilities:

- OCR
- Reading bet values
- Reading pot values
- Detecting board cards
- Detecting stacks
- Detecting dealer button

Recognition operates only on **image regions**.

It must not control session flow.

---

# solver/

Responsible for interacting with solver data.

Responsibilities:

- Loading solver files
- Mapping GameState to solver nodes
- Retrieving strategies
- Returning decision recommendations

---

# ui/

Responsible for visual interaction with the user.

Examples:

- Main menu
- Debug window
- Calibration overlay
- HUD overlays

Rules:

- UI must not perform OCR
- UI must not read screenshots
- UI must not contain solver logic

UI receives structured data from controllers.

---

# configs/

Configuration and calibration data.

Examples:

- table calibration
- seat layouts
- region definitions
- runtime settings

Config files contain **data only**.

---

# assets/images/

Static image assets used by the system.

Examples:

- anchor images
- template matching images
- card templates
- UI references

---

# utils/

Generic helpers.


Rules:

- Keep this folder small
- Do not put domain logic here
- Do not put recognition logic here

---

# tests/

Automated tests.

Tests should validate:

- recognition accuracy
- region mapping
- solver lookup
- domain state logic

---

# Architecture Rules

Dependency direction must follow: controllers -> services -> domain

- UI may call controllers.
- Controllers may call services.
- Services may create domain objects.
- Domain must remain independent.

---

# Refactoring Rules

- Do not perform large rewrites in one step
- Refactor incrementally
- Preserve behavior unless explicitly asked
- Prefer moving code first before redesigning
- Keep the application runnable after each step
- Update imports carefully
- Verify the new structure works before removing old code

---

# Performance

This project runs in real time.

When implementing code:

- Avoid heavy computations in frame loops
- Avoid repeatedly loading assets
- Reuse OCR instances
- Cache frequently used data
- Minimize disk I/O during gameplay
- Keep detection pipelines lightweight

---

# Coding Guidelines for AI Agents

When modifying this project, AI agents must follow these rules.

## 1. Preserve Architecture

Never mix responsibilities across layers.
Examples of forbidden combinations:
- UI + OCR in the same class
- Solver logic inside recognition modules
- Screen capture inside UI code
- Table geometry mixed with domain models


## 2. Prefer Small Classes
- Each class should have a single responsibility.
- Avoid large "god classes".


## 3. Prefer Small Refactors

When refactoring:

- change only one concern at a time
- keep diffs small
- avoid rewriting working systems

## 4. Maintain Pipeline Integrity

- Always respect the processing pipeline
- Never skip layers.

## 5. Prefer Explicit Code

Prefer:

- clear variable names
- explicit data structures
- dataclasses when appropriate
- type hints when helpful

Avoid hidden behavior.

---

## 6. Do Not Introduce New Dependencies Without Reason

External libraries must only be added if strictly necessary.

---

# What to Avoid

- Large refactors without clear necessity
- Mixing responsibilities across modules
- Introducing unnecessary dependencies
- Rewriting working code without justification
- Hardcoding UI coordinates without calibration support





