# Contributing to ORION BAS AI Copilot

Thank you for contributing to the **ORION BAS AI Copilot** project for the Bharatiya Antariksh Station (BAS).

To maintain aerospace mission-critical standards, all contributions must strictly adhere to the guidelines below.

---

## 1. Development Principles

1. **Safety & Determinism First**: Space station software cannot panic or fail silently. Every subsystem must handle edge conditions with explicit typed errors.
2. **Strict Typing**: All Python code must satisfy `mypy --strict`. Avoid `Any` unless interfacing with untyped C-bindings.
3. **No Dead Code or Fake Implementations**: If an interface method is not yet operational, raise `NotImplementedError("NOT IMPLEMENTED: <subsystem>")`. Never simulate AI outputs.
4. **Air-Gap Compliance**: No third-party network telemetry or external service calls are permitted.

---

## 2. Contribution Workflow

1. Create a descriptive feature branch from `main`:
   ```bash
   git checkout -b feat/bas-perception-yolo-interface
   ```
2. Ensure local environment passes all quality checks:
   ```bash
   python scripts/lint.py
   python scripts/format.py
   python scripts/test.py
   ```
3. Submit a Pull Request targeting `main`. Ensure all CI checks pass.
4. Obtain mandatory approvals from designated `@isro-bas` CODEOWNERS.

---

## 3. Commit Message Conventions

We follow Conventional Commits:
- `feat(perception): add camera frame capture contract`
- `fix(db): correct UUID column definition in Step entity`
- `docs(standards): document microgravity evaluation protocol`
- `ci(actions): add bandit security scanning step`
