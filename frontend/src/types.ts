/**
 * TypeScript types matching the backend API.
 */

export type Route = "local" | "api";
export type Mode = "live" | "replay";

export interface QueryRequest {
  db_id: string;
  question: string;
}

export interface QueryResult {
  route_to: Route;
  confidence: number;
  predicted_sql: string;
  gold_sql?: string;
  correct: boolean;
  latency_ms: number;
  result?: {
    columns: string[];
    rows: any[][];
  };
}

export interface RouteResponse extends QueryResult {}

export interface Config {
  layer: number;
  threshold: number;
  alpha: number;
  delta: number;
  student: string;
  teacher: string;
  mode: Mode;
  costs: Record<string, number>;
}

export interface Table {
  name: string;
  columns: string[];
}

export interface Database {
  db_id: string;
  tables: Table[];
  schema?: string;
}

export interface Question {
  question: string;
  route_to: Route;
  confidence: number;
  predicted_sql?: string;
  gold_sql?: string;
  correct?: boolean;
  latency_ms?: number;
}

export interface ParetoPoint {
  cost: number;
  accuracy: number;
  on_frontier: boolean;
}

export interface Pareto {
  points: ParetoPoint[];
}

export interface Summary {
  overall_accuracy: number;
  local_accuracy: number;
  api_accuracy: number;
  avg_latency_ms: number;
  cost_reduction_pct: number;
  by_database?: Record<string, number>;
}

export interface LayerData {
  layer: number;
  frac: number;
  sep_auroc: number;
  acc_auroc: number;
}

export interface CalibrationBin {
  conf: number;
  freq: number;
  n: number;
}

export interface Calibration {
  ece: number;
  bins: CalibrationBin[];
}

export interface AblationRow {
  variant: string;
  trainable_params: number;
  greedy_acc: number;
  sep_auroc: number;
  acc_at_20pct_esc: number;
}
