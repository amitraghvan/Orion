# Security Threat Model & Attack Surface Analysis

## Threat Vectors
1. **Malicious Model Weights**: Untrusted model binaries could contain arbitrary code execution payloads (e.g. pickled PyTorch `.pt` exploits).
   - *Mitigation*: Only ONNX, TensorRT engines, and SafeTensors formats are loaded. Checksum verification enforced before runtime deserialization.
2. **Directory Traversal**: Malicious input attempting to access root partitions or station control buses.
   - *Mitigation*: `orion.core.security.resolve_safe_path` enforces strict sandbox jail.
3. **Telemetry Flood / Denial of Service**: Excessive camera buffer allocation crashing system memory.
   - *Mitigation*: Bounded ring queues with drop-oldest eviction semantics.
