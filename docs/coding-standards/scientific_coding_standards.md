# Scientific Coding Standards for ORION BAS AI Copilot

## 1. Naming Conventions
- **Modules & Packages**: lowercase with underscores (`orion_ai`, `camera_driver.py`).
- **Classes & Pydantic Models**: PascalCase (`BoundingBox2D`, `ExperimentSpecification`).
- **Interfaces & Protocols**: PascalCase with `Interface` or `Protocol` suffix (`DetectorInterface`, `CameraDriverInterface`).
- **Functions & Methods**: snake_case verbs (`detect_objects()`, `validate_step()`).
- **Constants**: UPPER_SNAKE_CASE (`DEFAULT_SEED`, `MAX_BUFFER_SIZE`).

## 2. Architecture & Module Boundaries
- Strict separation between Perception (`ai`), Mission Control (`backend`), Data Platform (`datasets`), and Presentation (`frontend`).
- Zero direct model inference in backend controllers; all inference is mediated via typed schemas and interfaces.
- Zero mock inference outputs. Unfinished components must raise `NotImplementedError("NOT IMPLEMENTED: <subsystem>")`.

## 3. Documentation Style
- All public classes, functions, and interfaces must have Google-style Python docstrings.
- Docstrings must specify inputs, outputs, and raised exceptions.
- Complex mathematical or temporal algorithms must cite relevant research papers.

## 4. Strict Typing Philosophy
- All code must pass `mypy --strict`.
- Avoid `Any` unless interfacing with raw C/C++ libraries (e.g. ctypes/OpenCV bindings).
- Use `typing_extensions` for modern typing constructs compatible with Python 3.11.

## 5. Testing Philosophy
- Write tests alongside interfaces to prove contract correctness.
- Deterministic random seeds (`seed=42`) for reproducibility.
- Never use live hardware or network sockets in unit test suites.

## 6. Logging Philosophy
- Use structured key-value logging via Structlog.
- Always include `correlation_id` and mission context (`run_id`, `experiment_id`).
- Never log raw passwords, authorization tokens, or raw uncompressed image frames.

## 7. Error Handling Philosophy
- All domain exceptions must inherit from `OrionBaseException`.
- Exceptions must include a machine-readable `code` and structured `details` dictionary.
- Fail fast and fail safe: critical errors must transition state machines to a secure hold state.

## 8. Research Philosophy
- All novel AI models must be accompanied by a structured research document in `docs/research/`.
- Benchmarks must measure latency (p50, p95, p99), memory consumption, and thermal profile alongside accuracy.
