// Shared TypeScript types for the application

export interface LabeledFact {
  id: string;
  fact_type: string;
  description?: string;
  fields?: Record<string, unknown>;
  in_scope: boolean;
  matched_ids: string[];
  status: "TP" | "FP" | "FN";
}

export interface JudgeResult {
  gold_facts: LabeledFact[];
  predicted_facts: LabeledFact[];
  notes?: string;
}

export interface SchemaOverlapData {
  jaccard: number;
  missing_fields: string[];
  extra_fields: string[];
  intersection_count: number;
  union_count: number;
}

export interface CharacteristicVote {
  id: number;
  characteristic_id: number;
  characteristic_name: string;
  vote: boolean;
  reasoning: string;
  metrics?: Record<string, unknown>;
  result_data?: Record<string, unknown>;
}

export interface EvaluationResult {
  id: number;
  transcript_id: number;
  transcript_name: string;
  extracted_data: Record<string, unknown>;
  initial_extraction?: Record<string, unknown>;
  review_data?: {
    summary?: string;
    missing_items?: Array<{
      category: string;
      description: string;
      evidence?: string;
    }>;
    hallucinated_items?: Array<{
      category?: string;
      field_path: string;
      extracted_value?: unknown;
      reasoning: string;
    }>;
    issues?: Array<{
      type: string;
      field_path: string;
      description: string;
    }>;
  };
  final_extraction?: Record<string, unknown>;
  schema_overlap_data?: SchemaOverlapData;
  final_score: number;
  characteristic_votes: CharacteristicVote[];
  judge_result?: JudgeResult;
}

export interface Evaluation {
  id: number;
  experiment_id: number;
  judge_id: number;
  status: string;
  started_at?: string;
  completed_at?: string;
  schema_stability?: number;
  results?: EvaluationResult[];
}

export interface Progress {
  status: string;
  current?: number;
  total?: number;
  message?: string;
}

export interface Experiment {
  id: number;
  name: string;
  prompt: string;
  schema_json: string;
  model: string;
  enable_two_pass?: boolean;
  created_at?: string;
}

export interface Judge {
  id: number;
  name: string;
  model: string;
  judge_config?: Record<string, unknown>;
}

export interface Transcript {
  id: number;
  name: string;
  content: string;
}
