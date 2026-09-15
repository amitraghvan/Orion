# ORION Phase 1.5 — Change Ledger
**SIH26174 | Multimodal Human–Object Interaction Intelligence**

| ID | Issue | Source | Severity | Impact | Current State | Required Action | Verification | Status |
|---|---|---|---|---|---|---|---|---|
| CL-001 | No hand perception pipeline | Audit G1 | P0 | Cannot detect hands for HOI | Implemented | Create `ai/src/orion_ai/hand/` with schemas, interfaces, pose-based extractor | 20 golden scenarios pass; hand extraction verified | ✅ DONE |
| CL-002 | No object detection for protocol objects | Audit G2 | P0 | Cannot verify which object astronaut interacts with | Implemented | Add object detection interface + YOLO multi-class or second detector | ObjectDetector interface & YOLO multi-class operational | ✅ DONE |
| CL-003 | Object tracking not wired | Audit G3 | P0 | Objects lack temporal identity | Implemented | Wire ByteTracker for object detections in coordinator | ByteTracker tracks objects with distinct IDs | ✅ DONE |
| CL-004 | No person→hand association | Audit G4 | P0 | Cannot attribute hand to correct astronaut | Implemented | Implement wrist-keypoint-based hand region extraction | Unit test with 1 and 2 persons pass (SC-10) | ✅ DONE |
| CL-005 | No hand-object association | Audit G5 | P0 | Cannot determine which hand holds which object | Implemented | Implement spatial distance + IoU gated association | Bipartite Hungarian matching verified (SC-01-20) | ✅ DONE |
| CL-006 | No interaction state machine | Audit G6 | P0 | Cannot track temporal interaction lifecycle | Implemented | Implement NO_INTERACTION→APPROACHING→NEAR→CONTACT→GRASPING→MANIPULATING→RELEASING→LOST | SC-02, SC-04, SC-05, SC-06, SC-07, SC-15 pass | ✅ DONE |
| CL-007 | No multimodal evidence schema | Audit G7 | P0 | Cannot enrich protocol decisions | Implemented | Create MultimodalActivityEvidence, EvidenceQuality schemas | Contract test in test_hoi_scenarios.py | ✅ DONE |
| CL-008 | No multimodal fusion engine | Audit G8 | P0 | Cannot combine modalities | Implemented | Implement deterministic fusion (Levels 0-3) | DeterministicMultimodalFusion unit tests pass | ✅ DONE |
| CL-009 | No evidence quality computation | Audit G9 | P1 | Cannot assess overall observation reliability | Implemented | Implement composite quality from pose/hand/object/interaction | EvidenceQualityAssessor unit tests pass | ✅ DONE |
| CL-010 | No conflict handling | Audit G10 | P1 | Conflicting modalities silently ignored | Implemented | Implement CONFLICTING_EVIDENCE state | SC-11 modality conflict scenario passes | ✅ DONE |
| CL-011 | Interaction stubs never implemented | Audit G11 | P1 | InteractionDetectorInterface is dead code | Implemented | Replace with real Phase 1.5 implementation | Replaced with real geometry + associator + state machine | ✅ DONE |
| CL-012 | No HOI events in event taxonomy | Audit G12 | P1 | Cannot stream HOI updates | Implemented | Add HandInteractionStarted/Updated/Ended, ObjectInteractionRecognized, etc. | 8 new HOI events added to events/schemas.py | ✅ DONE |
| CL-013 | bbox_iou duplicated | Audit G13 | P2 | Maintenance risk | Implemented | Extract to shared `ai/src/orion_ai/geometry/iou.py` | Shared module extracted, imported across codebase | ✅ DONE |
| CL-014 | No HOI display in HUD | Audit G14 | P2 | Astronaut copilot lacks interaction context | Implemented | Add hand/object/interaction/evidence cards | Frontend Vite build passes, HUD rendering live | ✅ DONE |
| CL-015 | ModelMetadata.task literal incomplete | Audit G15 | P2 | Cannot register hand/object models | Implemented | Add "hand" and "object" to Literal | Mypy strict passes | ✅ DONE |
| CL-016 | No license audit | Audit G16 | P2 | Provenance not documented | Implemented | Create docs/phase_1_5_license_audit.md | docs/phase_1_5_license_audit.md created | ✅ DONE |
| CL-017 | No ROI configuration | Audit G17 | P3 | No spatial filtering for glovebox | Implemented | Add optional ROI config in settings | Glovebox ROI filtering functional | ✅ DONE |
| CL-018 | StructuredObservation missing HOI fields | Audit | P0 | Cannot propagate HOI through pipeline | Implemented | Extend with optional multimodal fields | StructuredObservation contract updated | ✅ DONE |
| CL-019 | PipelineMetrics missing HOI latencies | Audit | P1 | Cannot profile new stages | Implemented | Add hand/object/interaction/fusion latency | PipelineMetrics profiling fields integrated | ✅ DONE |
| CL-020 | No hand/object WebSocket telemetry | Audit | P1 | Frontend cannot receive HOI data | Implemented | Add HOI event types to WS | telemetry_ws.py broadcasts HOI and evidence | ✅ DONE |
