# Architectural Decision Record (ADR) 001: Monorepo Architecture & Package Isolation

## Status
**ACCEPTED** (2026-03-15)

## Context
The Bharatiya Antariksh Station (BAS) AI Copilot requires co-evolution of deep learning perception modules, high-throughput asynchronous backend streaming, deterministic experiment state validation, and air-gapped mission control telemetry. Monolithic repositories introduce tight coupling and dependency conflicts, while multi-repo architectures cause drift in shared type contracts and schema synchronization.

## Decision
Adopt a unified polyglot Monorepo managed via:
1. `uv` workspaces for Python 3.11 with strict boundary enforcement between `backend`, `ai`, and `datasets`.
2. Standard Node LTS + npm for the static React telemetry mission control frontend.
3. Declarative Pydantic v2 schemas as single source of truth for both REST/WebSocket API and internal event buses.

## Consequences
- **Positive**: Atomic commits across backend, AI models, and frontend telemetry schemas. Single CI pipeline gate for aerospace compliance.
- **Negative**: Requires strict discipline to prevent leakage of model logic into backend or UI layers.
