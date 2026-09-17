# Offline-First Architectural Principles

Space station software must operate under the assumption of **complete network isolation** (air-gap mode).

## Core Rules
1. **Zero External Dependencies at Runtime**: No CDN scripts, no cloud model downloads, no remote API calls. All model weights, fonts, and assets must be statically bundled or loaded from local filesystem.
2. **Local Persistence First**: All telemetry, experiment steps, and recording manifests are committed to local SQLite / PostgreSQL and filesystem storage before any network broadcast.
3. **Deterministic State Recovery**: In the event of a sudden station power transient, the system restores the exact step, frame index, and experiment state from persistent storage within 5 seconds of reboot.
4. **Local Acoustic Synthesis**: Text-to-speech annunciation uses embedded offline engines (`espeak-ng` or local neural TTS), never cloud speech services.
