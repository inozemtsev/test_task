Concept: Configurable LLM Judge with UI-Driven Profiles
1. Goal

Right now judge behavior is controlled by ad-hoc prompt edits in the UI. This is fragile and makes metrics unstable.

The goal is:

Move all judge behavior settings into a structured config managed by the UI.

Use that config to drive a single LLM judge call per evaluation.

Compute precision/recall and other metrics outside the LLM from a stable, structured result.

In other words: UI controls → judge_config JSON → one judge call → structured matches → metrics.

2. UI Layer: from sliders/toggles to judge_config

In the UI the user should no longer edit raw prompts to “tune” the judge. Instead, the UI exposes controls that map directly to fields in a judge_config object.

Examples of UI elements:

Judge profile selector

Dropdown: Strict, Lenient, Client-specific, Custom.

Internally sets profile_name (e.g. "strict", "lenient").

Fact types in scope

Multi-select checklist: Assets, Debts, Income, Pensions, etc.

Maps to fact_types_in_scope: ["assets", "debts", ...].

Equivalence settings

Numeric tolerance slider: ±X % → numeric_tolerance_percent.

Date granularity dropdown: Day / Month / Year → date_granularity.

Toggle: “Ignore minor wording differences” → ignore_minor_wording_diffs.

Toggle: “Case-insensitive string comparison” → case_insensitive_strings.

Scoring rules

Toggle: “Require all fields to match exactly” → require_all_fields_match.

Multi-select: “Key fields that must match” → required_key_fields.

Toggle: “Allow partial matches to still count as correct” → allow_partial_matches.

(Optional) Advanced free-text notes

A text area “Advanced judge notes (optional)”.

Stored as extra_instructions in config, but this is an additive field, not the main control mechanism.

All of these UI controls are combined into a single machine-readable judge_config JSON. The user never edits the system prompt directly; they just manipulate UI settings.

The UI must:

Always show the current judge_config state (invisible to user or in a debug panel).

Save/restore configs per “profile” so users can switch profiles and reuse settings.

3. Core Data Objects

Conceptually, the system operates on:

transcript: conversation text.

predicted_facts: facts extracted by the model being evaluated.

Optional gold_facts: reference facts (if available; otherwise the judge derives them).

judge_config: produced by the UI as described above.

These four items are the complete input for the judge.

4. Judge Call: one prompt, one run, both metrics

The backend (or Claude Code logic) provides a function like:

runJudge(transcript, predicted_facts, judge_config, [optional gold_facts]) → JudgeResult


Conceptually it works as follows:

Build a static system prompt describing the judge’s job:

You are an evaluator of fact extraction.

You receive transcript, predicted facts, optional gold facts, and a judge_config.

You must:

Apply judge_config to decide which facts are in scope.

Decide which gold and predicted facts represent the same real-world fact.

Label each gold fact as TP or FN.

Label each predicted fact as TP or FP.

You must output only JSON matching the agreed schema (no text around it).

You do not compute precision/recall; you only label facts.

This system prompt is constant and does not depend on the UI.

Build the user/content payload:

Include:

transcript (string).

judge_config (JSON from the UI).

predicted_facts (JSON).

Optional gold_facts (JSON).

Include or reference the expected JSON shape for the output (gold_facts + predicted_facts with status and match links).

Call the LLM with:

temperature = 0.

Strict JSON output (response_format with schema, or equivalent).

Optionally a fixed seed for determinism.

The LLM returns a JudgeResult:

gold_facts: list of gold facts with:

id

fact_type

fields

in_scope

matched_prediction_ids

status: "TP" | "FN"

predicted_facts: list of predicted facts with:

id

fact_type

fields

in_scope

matched_gold_ids

status: "TP" | "FP"

Optional notes from the judge.

The backend validates JSON and exposes JudgeResult to the rest of the system.

Crucially:

Precision and recall are not computed inside the LLM.

Both metrics are computed from the same JudgeResult in code, so denominators are consistent:

Precision = TP / (TP + FP) from predicted_facts.

Recall = TP / (TP + FN) from gold_facts.

5. Metrics and UI Display

A separate component (no LLM) computes metrics from JudgeResult:

Precision, recall, F1.

Hallucination rate (1 − precision).

Coverage (recall).

The UI then:

Displays metrics (usually as percentages).

Optionally shows:

Selected judge profile name.

Key parts of judge_config (e.g. “Strict, tolerance ±5%, day-level dates”).

Expandable panel to inspect TP/FP/FN counts and examples.

The user understands that:

Changing the judge profile or settings in the UI updates judge_config.

Re-running evaluation with a different profile will produce different metrics, but they are computed in a consistent way from a single judge run.

6. Summary of Responsibilities

UI

Provides controls for judge behavior.

Produces and persists a structured judge_config object.

Shows metrics and (optionally) confusion details.

Judge module (Claude Code)

Accepts transcript, predicted_facts, optional gold_facts, and judge_config.

Builds a stable system prompt and payload.

Calls LLM once.

Returns JudgeResult = labeled facts + match links.

Metrics module

Pure function over JudgeResult.

Computes precision/recall/F1/hallucination/coverage.

No LLM calls.

This separates “how we configure the judge” (UI → config) from “how we evaluate” (one deterministic judge call → metrics), while still allowing dynamic tuning of judge behavior via the UI.