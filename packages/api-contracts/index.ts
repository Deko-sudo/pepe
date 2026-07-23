export interface HealthResponse {
  status: "ok" | "error";
  service: string;
}

export interface ReadinessResponse {
  status: "ready" | "degraded" | "error";
  service: string;
  dependencies: Record<string, "ok" | "error">;
}

export interface VersionResponse {
  name: string;
  service: string;
  version: string;
  environment: string;
}
