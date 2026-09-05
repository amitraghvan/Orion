import type { StationHealthReport } from "../types/telemetry";

const BASE_URL = "/api/v1";

/**
 * Service client contract for communicating with FastAPI backend.
 */
export async function fetchHealthLiveness(): Promise<{ status: string }> {
  const response = await fetch(`${BASE_URL}/health/live`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchStationMetadata(): Promise<StationHealthReport> {
  const response = await fetch(`${BASE_URL}/metadata/info`);
  if (!response.ok) {
    throw new Error(`Failed to fetch metadata: ${response.statusText}`);
  }
  return response.json();
}
