/**
 * Authentication and token management service for ORION BAS AI Copilot HUD.
 */

const TOKEN_STORAGE_KEY = "orion_station_token";

let inMemoryToken = "";

export function getAuthToken(): string {
  if (inMemoryToken) return inMemoryToken;
  if (typeof window === "undefined") return "";
  try {
    const stored =
      (typeof sessionStorage !== "undefined" && sessionStorage.getItem(TOKEN_STORAGE_KEY)) ||
      (typeof localStorage !== "undefined" && localStorage.getItem(TOKEN_STORAGE_KEY));
    if (stored) return stored;
  } catch {
    // Ignore storage access errors
  }

  const envToken = (import.meta as unknown as { env?: { VITE_ORION_AUTH_TOKEN?: string } }).env
    ?.VITE_ORION_AUTH_TOKEN;
  if (envToken) return envToken;

  return "";
}

export function setAuthToken(token: string): void {
  inMemoryToken = token;
  try {
    if (typeof sessionStorage !== "undefined") {
      sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    }
  } catch {
    // Ignore storage write errors
  }
}

export function clearAuthToken(): void {
  inMemoryToken = "";
  try {
    if (typeof sessionStorage !== "undefined") sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    if (typeof localStorage !== "undefined") localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Ignore storage errors
  }
}

export function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  if (!token) return {};
  return {
    Authorization: `Bearer ${token}`,
  };
}

export async function ensureStationToken(forceFresh = false): Promise<string> {
  if (!forceFresh) {
    const existing = getAuthToken();
    if (existing) return existing;
  } else {
    clearAuthToken();
  }

  try {
    const res = await fetch("/api/v1/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: "station-operator",
        role: "operator",
      }),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.access_token) {
        setAuthToken(data.access_token);
        return data.access_token;
      }
    }
  } catch (err) {
    console.warn("Failed to auto-acquire station token:", err);
  }
  return "";
}

export async function getAuthHeadersAsync(): Promise<Record<string, string>> {
  const token = await ensureStationToken();
  if (!token) return {};
  return {
    Authorization: `Bearer ${token}`,
  };
}
