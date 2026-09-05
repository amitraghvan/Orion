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
  confidence: number;
  is_nominal: boolean;
}

export interface TelemetryFrame {
  station_id: string;
  frame_index: number;
  timestamp_utc: string;
  detections: DetectionTarget[];
  poses: HumanPose[];
  activity?: ActivityPrediction;
}

export interface StationHealthReport {
  station_id: string;
  environment: string;
  version: string;
  timestamp: string;
  subsystems: Record<string, SubsystemStatus>;
}
