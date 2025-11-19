# Evaluation Enhancement Plan

Goal: redesign `run_judge()` so that fact scope filtering happens in code and TP/FP/FN adjudication is done via two targeted LLM passes (gold→predicted and predicted→gold) with deduplication of matches.

## Current Behavior Recap
- The judge receives gold facts (already generated elsewhere) and predicted facts.
- It sends both lists plus config to the LLM once; the model labels each element with TP/FP/FN and match links.
- Entity type scoping happens inside the prompt, so out-of-scope items still consume tokens and may get mislabeled.

## Key Requirements
1. Apply `entity_types` filtering before calling the LLM.
2. Make one LLM call per gold fact (with all predicted facts in context) to classify it as TP or FN and capture the matched predicted fact ID when applicable.
3. Make one LLM call per predicted fact (with all gold facts in context) to classify it as TP or FP and capture the matched gold fact ID when applicable.
4. Track match IDs in a structured schema that the LLM must output.
5. Deduplicate matches so a gold fact links to at most one predicted fact and vice versa; resolve conflicts deterministically.

## Proposed Implementation Steps

### 1. Preprocess Facts in Code
- Derive `in_scope` flags and filtered lists before any LLM call:
  - Build `allowed_entity_types = set(judge_config.get("entity_types") or [])`.
  - For each fact in `gold_facts` and `predicted_facts`, set `in_scope = fact["fact_type"] in allowed_entity_types` (default to `True` when list empty).
  - Maintain both the original lists (with all entries) and scoped lists (only those in scope) for judging; out-of-scope facts can skip LLM adjudication and be labeled `status="OUT_OF_SCOPE"`.
- Persist canonical IDs (existing `id` fields).

### 2. Gold-Centric Judging Loop
- Iterate over each scoped gold fact and call the LLM with:
  - System instructions describing the comparison rules (matching_rules list)
  - User prompt containing the single gold fact, the entire scoped predicted list, and matching rules (tolerances, fields, etc.).
  - STRICT Structured output schema such as:
    ```json
    {
      "type": "object",
      "properties": {
        "gold_fact_id": {"type": "string"},
        "status": {"enum": ["TP", "FN"]},
        "matched_predicted_id": {"type": "string", "nullable": true},
        "reasoning": {"type": "string"}
      },
      "required": ["gold_fact_id", "status"],
      "additionalProperties": false
    }
    ```
Check the existing evaluation schema for reference.
  
- The judge must return TP only when a unique predicted fact matches under the provided rules. FN implies `matched_predicted_id=null`.
- Capture these responses in a dictionary keyed by gold fact ID along with the matched predicted ID (if any).

### 3. Predicted-Centric Judging Loop
- Repeat the process for each scoped predicted fact using a mirrored schema:
    ```json
    {
      "type": "object",
      "properties": {
        "predicted_fact_id": {"type": "string"},
        "status": {"enum": ["TP", "FP"]},
        "matched_gold_id": {"type": "string", "nullable": true},
        "reasoning": {"type": "string"}
      },
      "required": ["predicted_fact_id", "status"],
      "additionalProperties": false
    }
    ```
- Prompts contain the single predicted fact plus the full scoped gold list.
- Store outputs keyed by predicted fact ID.

### 4. Deduplication & Match Resolution
- After collecting both directions:
  - Build candidate match pairs from gold-side TP decisions and predicted-side TP decisions.
  - Potential conflicts:
    - A predicted fact claims TP but the referenced gold fact labeled FN -> label gold fact as tp, mention it in a description field
    - A predicted fact claims FP but the referenced gold fact labeled TP -> label gold fact as fp, mention it in a description field
    - Multiple gold facts match the same predicted fact -> don't do anything, it's correct.
    - Multiple predicted facts match the same gold fact -> mark the first one as tp, the others as fp. add this note as a description field to them
  - Resolution strategy:
    Mark remaining unmatched elements as FN (gold) or FP (predicted).
  - Update `matched_ids` arrays accordingly and ensure bijection (one-to-one) by clearing conflicting links.
- Record dedup reasoning (e.g., `dedup_notes`) for debugging/logging.

### 5. Final Output Assembly
- Merge deduplicated statuses back into the full fact lists:
  - Scoped facts get TP/FP/FN statuses per dedup results.
  - Out-of-scope facts retain original data with `status="OUT_OF_SCOPE"` and empty `matched_ids`.
- Include both loops' reasoning (maybe aggregated) in the final `notes` or per-fact metadata.

### 6. Additional Considerations
- **Performance:** Number of LLM calls equals `len(scoped_gold) + len(scoped_predicted)`; consider running them in parallel.
- **Prompt Size:** Since each call includes the full opposing list, enforce truncation safeguards (token counting) and fallback messaging if context is too large.
- **Testing Plan:**
  1. Unit-test preprocessing to ensure correct in-scope detection.
  2. Add mocks for LLM responses to test dedup resolver logic.
  3. Regression-test end-to-end evaluation with synthetic gold/predicted pairs covering TP/FP/FN mix and duplicate matches.

This plan should guide the upcoming refactor before touching `run_judge()` implementation.
