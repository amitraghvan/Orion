# Air-Gapped Space Station Deployment Protocol

## Procedure
1. **Container Image Verification**:
   - Container images must be exported as tarballs on ground (`docker save`).
   - Cryptographic signatures and SHA-256 hashes must match flight delivery manifest.
2. **Installation via Ground Upload / Physical Media**:
   - Transferred via radiation-shielded encrypted NVMe drives or high-bandwidth S-band pass.
   - Loaded using `docker load -i orion_backend.tar`.
3. **Environment Configuration**:
   - Configure local hardware profile (`configs/hardware/edge_jetson.yaml` or `flight_workstation.yaml`).
   - Run `python scripts/doctor.py` to verify system health before initiating flight experiments.
