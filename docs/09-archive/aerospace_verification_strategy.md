# Aerospace Verification & Testing Strategy

## Test Pyramid
1. **Unit Tests (40%)**:
   - Configuration hierarchy loading, schema validation, exception formatting.
   - Fast (< 100ms), zero external I/O.
2. **Contract & Schema Tests (30%)**:
   - Pydantic models validate against sample YAML and JSON payloads.
   - Hypothesis property-based fuzzing for edge boundary values.
3. **Integration Tests (20%)**:
   - In-memory SQLite async database engine migrations and entity persistence.
4. **Hardware-in-the-Loop & Benchmarks (10%)**:
   - Frame latency, memory leak detection over 24-hour continuous burn-in.
