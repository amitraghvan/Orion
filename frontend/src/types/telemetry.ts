/**
 * Telemetry and AI perception contracts mirroring Python backend schemas.
 */

export type SubsystemStatus = "HEALTHY" | "DEGRADED" | "UNHEALTHY" | "OFFLINE";

export interface BoundingBox2D {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

export interface DetectionTarget {
  class_id: number;
  class_name: string;
  confidence: number;
  box: BoundingBox2D;
  track_id?: number;
}

export interface Keypoint2D {
  id: number;
  name: string;
  x: number;
  y: number;
  score: number;
}

export interface HumanPose {
  person_id: number;
  bbox: BoundingBox2D;
  topology: string;
  keypoints_2d: Keypoint2D[];
  overall_confidence: number;
}

export interface ActivityPrediction {
  activity_name: string;
  phase?: "START" | "UPDATE" | "CHANGE" | "END";
  confidence: number;
  probabilities?: Record<string, number>;
  uncertainty_status?: "NOMINAL" | "UNKNOWN" | "UNCERTAIN" | "WARMING_UP" | "DEGRADED";
  is_nominal: boolean;
  model_version?: string;
}

export interface ActivityRecognitionResult {
  track_id: number;
  top_prediction: ActivityPrediction;
  candidates?: ActivityPrediction[];
  uncertainty_status: string;
  latency_ms: number;
}

export interface PipelineMetrics {
  camera_latency_ms: number;
  detection_latency_ms: number;
  object_latency_ms?: number;
  pose_latency_ms: number;
  hand_latency_ms?: number;
  tracking_latency_ms: number;
  har_latency_ms?: number;
  interaction_latency_ms?: number;
  fusion_latency_ms?: number;
  pipeline_latency_ms: number;
  fps: number;
  dropped_frames_total: number;
}

export type HandSide = "left" | "right" | "unknown";
export type HandState = "observed" | "partial" | "occluded" | "missing" | "invalid";

export interface HandObservation {
  hand_id: string;
  side: HandSide;
  person_track_id: number;
  wrist_keypoint?: Keypoint2D | null;
  region_bbox?: BoundingBox2D | null;
  confidence: number;
  state: HandState;
  frame_index: number;
  timestamp: string;
  source_id: string;
}

export interface ObjectObservation {
  object_id: string;
  class_name: string;
  bbox: BoundingBox2D;
  confidence: number;
  track_id?: number | null;
  frame_index: number;
  timestamp: string;
  source_id: string;
}

export type InteractionState =
  | "no_interaction"
  | "approaching"
  | "near"
  | "contact"
  | "grasping"
  | "manipulating"
  | "releasing"
  | "lost"
  | "unknown";

export interface InteractionObservation {
  hand_id: string;
  object_id: string;
  person_track_id: number;
  state: InteractionState;
  distance_normalized: number;
  overlap_ratio: number;
  approach_velocity?: number;
  contact_persistence_frames?: number;
  confidence: number;
}

export type EvidenceQualityLevel = "HIGH" | "MEDIUM" | "LOW" | "INSUFFICIENT";
export type EvidenceState =
  | "FULL_EVIDENCE"
  | "PARTIAL_EVIDENCE"
  | "CONFLICTING_EVIDENCE"
  | "INSUFFICIENT_EVIDENCE";

export interface EvidenceQuality {
  pose_quality: number;
  actor_identity_quality: number;
  hand_quality: number;
  object_quality: number;
  interaction_quality: number;
  temporal_stability: number;
  overall: EvidenceQualityLevel;
}

export interface MultimodalActivityEvidence {
  activity: string;
  person_track_id: number;
  hands: HandObservation[];
  objects: ObjectObservation[];
  interactions: InteractionObservation[];
  confidence: number;
  uncertainty_status: string;
  evidence_quality: EvidenceQuality;
  evidence_state: EvidenceState;
  window_start: number;
  window_end: number;
  frame_ids: number[];
  source_id: string;
  model_versions?: Record<string, string>;
}

export interface TelemetryFrame {
  type?: string;
  station_id: string;
  frame_index: number;
  timestamp_utc: string;
  source_id?: string;
  width?: number;
  height?: number;
  detections: DetectionTarget[];
  poses: HumanPose[];
  tracks?: any[];
  activity?: ActivityPrediction;
  activities?: ActivityRecognitionResult[];
  top_activity?: string | null;
  hands?: HandObservation[];
  objects?: ObjectObservation[];
  interactions?: InteractionObservation[];
  multimodal_evidence?: MultimodalActivityEvidence | null;
  metrics?: PipelineMetrics;
  pipeline_status?: string;
  image_jpeg?: string | null;
}

export interface CameraInfo {
  camera_id: string;
  source: string;
  is_active: boolean;
  is_file: boolean;
  target_fps: number;
  width: number;
  height: number;
  dropped_frames: number;
}

export interface StationHealthReport {
  station_id: string;
  environment: string;
  version: string;
  timestamp: string;
  subsystems: Record<string, SubsystemStatus>;
}

export type ProtocolFSMState =
  | "IDLE"
  | "LOADED"
  | "PRECHECK"
  | "RUNNING"
  | "STEP_IN_PROGRESS"
  | "STEP_COMPLETED"
  | "PAUSED"
  | "BLOCKED"
  | "COMPLETED"
  | "ABORTED"
  | "DEGRADED";

export type ProtocolDecisionStatus =
  | "VALID"
  | "INVALID_ACTION"
  | "OUT_OF_SEQUENCE"
  | "SKIPPED"
  | "STEP_UNCERTAIN"
  | "WAITING_FOR_EVIDENCE"
  | "TIMEOUT"
  | "COMPLETED";

export interface ProtocolStepInfo {
  step_id: string;
  step_number: number;
  description: string;
  expected_activity: string;
  status: "PENDING" | "ACTIVE" | "COMPLETED" | "ABORTED" | "PAUSED";
}

export interface NextStepGuidance {
  step_id: string;
  step_number: number;
  total_steps: number;
  expected_activity: string;
  expected_actions?: string[];
  instruction_text: string;
  nominal_duration_seconds: number;
  max_timeout_seconds: number;
  elapsed_seconds: number;
  remaining_nominal_seconds: number;
  hazard_warnings: string[];
  is_last_step: boolean;
  fsm_state: string;
}

export interface ExperimentStatusPayload {
  experiment_id: string;
  run_id: string;
  fsm_state: ProtocolFSMState;
  protocol_hash?: string;
  total_steps: number;
  current_step_index: number;
  current_step?: {
    step_id: string;
    step_number: number;
    description: string;
    expected_activity: string;
  } | null;
  recommendation?: NextStepGuidance | null;
  steps: ProtocolStepInfo[];
  actor_track_id?: number | null;
}

