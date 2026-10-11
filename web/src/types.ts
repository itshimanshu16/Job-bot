/** Shapes of data/jobs.json, written by the Python collector (jobradar/report.py). */

export interface TrackResume {
  file: string;
  use_for: string;
}

export interface TrackMeta {
  id: string;
  label: string;
  resumes: TrackResume[];
}

export interface CandidateMeta {
  degree?: string;
  graduation_year?: number;
  max_years_experience?: number;
}

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

  // Multi-track and resume metadata
  track: string;
  track_label: string;
  resume: string;
  resume_reason: string;
  track_scores: Record<string, number>;
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
  tracks?: TrackMeta[];
  candidate?: CandidateMeta;
}

export interface Payload {
  meta: Meta;
  jobs: Job[];
}

export type MarkStatus = "applied" | "hidden";

export interface Mark {
  status: MarkStatus;
  at: string; // ISO time the mark was made
  resume?: string;
}

export type Marks = Record<string, Mark>;

export type Tab = "review" | "new" | "applied" | "hidden";

export type Sort = "score" | "date";
