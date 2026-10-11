/** Shapes of data/jobs.json, written by the Python collector (jobradar/report.py). */

export interface Job {
  uid: string;
  source: string;
  company: string;
  title: string;
  url: string;
  apply_url: string;
  location: string;
  remote: boolean | null;
  posted: string | null;
  department: string;
  employment_type: string;
  seniority: string;
  score: number;
  reasons: string[];
  flags: string[];
  min_years: number | null;
  is_new: boolean;
  first_seen: string;
  llm_score: number | null;
  llm_reason: string;
  snippet: string;
}

export interface Board {
  source: string;
  slug: string;
  company: string;
  count: number;
  error: string;
}

export interface Meta {
  title: string;
  generated: string;
  first_run: boolean;
  total_fetched: number;
  boards_ok: number;
  boards: Board[];
  drops: Record<string, number>;
  notes: string[];
  keywords: string[];
}

export interface Payload {
  meta: Meta;
  jobs: Job[];
}

export type MarkStatus = "applied" | "hidden";

export interface Mark {
  status: MarkStatus;
  at: string; // ISO time the mark was made
}

export type Marks = Record<string, Mark>;

export type Tab = "review" | "new" | "applied" | "hidden";

export type Sort = "score" | "date";
