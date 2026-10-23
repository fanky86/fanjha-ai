export type BuildStatus =
  | "IDLE"
  | "PREPARING"
  | "COLLECTING_DATA"
  | "PREPROCESSING"
  | "TOKENIZING"
  | "TRAINING"
  | "EVALUATING"
  | "EXPORTING"
  | "VERIFYING"
  | "SUCCESS"
  | "WARNING"
  | "FAILED"
  | "CANCELLED";

export interface Build {
  id: string;
  status: BuildStatus;
  active_stage: string | null;
  overall_progress: number;
  config: Record<string, unknown>;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  error_summary: string | null;
  checkpoint_path: string | null;
  correlation_id: string;
  current_epoch: number | null;
  current_step: number | null;
  is_resumed: boolean;
}

export interface BuildSummary {
  id: string;
  status: BuildStatus;
  overall_progress: number;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  error_summary: string | null;
}

export interface LogEntry {
  id: number;
  timestamp: string;
  severity: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL";
  component: string;
  message: string;
  stack_trace?: string | null;
}

export interface Metric {
  id?: number;
  timestamp?: string;
  epoch?: number | null;
  global_step?: number | null;
  train_loss?: number | null;
  val_loss?: number | null;
  perplexity?: number | null;
  learning_rate?: number | null;
  throughput_tokens_per_sec?: number | null;
}

export interface Artifact {
  id: string;
  name: string;
  size_bytes: number;
  sha256: string;
  verified: boolean;
  artifact_type: string;
  created_at: string;
}

export interface SystemResources {
  cpu_percent: number;
  cpu_count: number;
  ram_used: number;
  ram_available: number;
  ram_total: number;
  disk_used: number;
  disk_free: number;
  disk_total: number;
  process_ram_used: number | null;
  gpu: Record<string, unknown> | string;
}

export interface DatasetInfo {
  path: string;
  size_bytes: number;
  documents: number | null;
  estimated_tokens: number | null;
  language?: string | null;
  source?: string | null;
  license?: string | null;
}
