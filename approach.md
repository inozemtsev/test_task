## Approach

### Synthetic Transcript Generation

I generate realistic financial advisor transcripts using a three-stage pipeline:

1. **Schema Development** - Create and validate a JSON schema that balances completeness with model capability
2. **Prompt Generation** - Create 34 diverse client personas across 17 persona types (young couples, retirees, high earners, etc.) with 2 instances each, covering 7 financial topics: clients information, assets, pensions, incomes, expenses, loans/mortgages, and savings/investments
3. **Transcript Synthesis** - Use GPT-5 to generate natural conversations following persona profiles

**Key characteristics:**
- Natural conversation flow (not rigidly structured by topic)
- Realistic level of specificity - mix of precise details and vague statements to resemble how people actually talk
- 30-60 minute conversation length
- Multiple financial topics per transcript (assets, debts, pensions, income, expenses)

For full details on the generation process, see [preparation/README.md](preparation/README.md).

[Generated example](preparation/generated_example.txt)

You can find more examples in the demo or in the attached Google Drive folder - see the links above.




### Structured Schema Design

The JSON schema for financial data extraction required careful balancing of **complexity** (capturing all relevant information) and **coverage** (not overwhelming the LLM's context window).

#### Key Constraints

**1. Depth Limit: Maximum 5 Levels of Nesting**

Example structure:
```
Level 1: { clients[], assets[], debts[] }
Level 2: assets[] { static {}, dynamic [] }
Level 3: static { asset_type {}, value {}, ... }
Level 4: asset_type { value "", citation "", call_time "" }
Level 5: citation { recorded_at "", is_estimate "" }
```

Going deeper than 5 levels causes:
- LLM confusion about where to place data
- Increased hallucination rates
- Slower extraction times
- Schema validation failures

**2. Fact-Oriented Structure**

The schema uses a "FactValue" pattern for trackable data:
```json
{
  "value": "Primary residence",
  "call_time": "00:15:32",
  "citation": "quoted from transcript",
  "recorded_at": "2024-03-15",
  "is_estimate": false,
  "value_as_of_date": "2024-03-01",
  "unit": "GBP"
}
```

This allows:
- Timestamp tracking for audit trails
- Distinguishing stated facts from advisor estimates
- Capturing temporal context (when was this true?)
- Tracking changes in opinions or estimates during the conversation

**3. JSON Schema Advanced Features**

I use:
- `$ref` for reusable definitions (e.g., FactValue, SnapshotValue)
- `allOf` for inheritance (SnapshotValue extends FactValue)
- `anyOf` for optional types (string or null)
- `required` fields vs. optional fields
- `additionalProperties: false` for strict validation

These features help LLMs represent the structure better than flat schemas.

[**Full schema example →**](preparation/schema_example.json)

#### Schema Development Process

Iterative refinement process:
1. Used ChatGPT to create a baseline schema (initial version was too permissive)
2. Test extraction on 2 template transcripts with loose schema
3. Analyze field coverage - which fields appear consistently
4. Identify duplicate or redundant fields  
5. Re-run on generated data and refine schema based on stability analysis
6. Re-test until stable results achieved

---

## Evaluation Methodology

The evaluation system is the **most critical component** for producing stable and verifiable results.

**Ground Truth Generation:** Ground truth facts are generated using the same LLM with a deliberately simple schema that only captures fact descriptions and types, without enforcing the complex structure used for extraction. This prevents bias toward any particular extraction schema and allows fair evaluation across different extraction approaches.

### Core Architecture: Dual-Pass 1-vs-All with Deduplication

**Problem:** Simple "compare all facts at once" approaches produce inconsistent TP/FP/FN labels due to:
- Order effects (which fact the LLM sees first)
- Attention limitations (missing matches in long lists)
- Ambiguous many-to-many relationships

**Solution:** A sophisticated multi-step judge system:

**Step 1: Ground Truth Generation**
```
Input: Raw transcript + Judge configuration (entity types, matching rules)
Output: List of gold facts that SHOULD be extracted
```
- Uses temperature=0 and seed=54321 for reproducibility
- One LLM call per (judge, transcript) pair
- Results stored in database for reuse across experiments
- Can be manually reviewed and edited by domain experts

**Step 2: Fact Extraction**
```
Input: Transcript + Extraction prompt + JSON schema
Output: Structured data with predicted facts
```
- Uses temperature=0 and seed=54321 for reproducibility
- Optional two-pass extraction with review step (see Session 3 in AGENTS.md)

**Step 3: Dual-Pass Judging (1-vs-All)**

**Pass 1: Gold fact evaluation** (Recall-focused)
- For EACH gold fact individually:
  - LLM sees: 1 gold fact + ALL predicted facts
  - Must output: `{status: "TP" or "FN", matched_predicted_id: "...", reasoning: "..."}`
  - If TP → must specify which predicted fact matches
- Parallelized (4 concurrent LLM calls) for speed
- Forces explicit attention to each expected fact

**Pass 2: Predicted fact evaluation** (Precision-focused)
- For EACH predicted fact individually:
  - LLM sees: 1 predicted fact + ALL gold facts  
  - Must output: `{status: "TP" or "FP", matched_gold_id: "...", reasoning: "..."}`
  - If TP → must specify which gold fact matches
- Also parallelized (4 concurrent)

**Step 4: Deduplication and Conflict Resolution**

After both passes, I have two perspectives on each fact. Conflicts are resolved:

1. **Disagreement Cases:**
   - Gold says "FN" but predicted says "TP to that gold" → Force gold to TP
   - Gold says "TP to predicted X" but predicted X says "FP" → Force gold to FN
   - Ensures consistency between both viewpoints

2. **Many-to-One Matches:**
   - Multiple predicted facts claim to match the same gold fact
   - Keep only the FIRST match (by document order)
   - Mark remaining predicted facts as FP
   - Prevents double-counting the same information

3. **Final Status Assignment:**
   - Gold fact is TP iff it has at least one matched predicted fact
   - Predicted fact is TP iff it has at least one matched gold fact
   - All unmatched gold facts → FN
   - All unmatched predicted facts → FP

**Step 5: Metric Computation**

Pure code-based calculation (no LLM):
```python
TP = count of matched facts
FP = count of predicted facts with no gold match
FN = count of gold facts with no predicted match

Precision = TP / (TP + FP)
Recall = TP / (TP + FN)
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

### Why This Approach Works

**Reproducibility:**
- Temperature=0 + seed=54321 on ALL LLM calls
- Same inputs always produce same outputs
- Experiments can be re-run to verify results

**Fairness:**
- Every gold fact gets equal attention (not buried in a long list)
- Every predicted fact evaluated independently
- No order effects or attention bias

**Verifiability:**
- Reasoning stored for every TP/FP/FN decision
- Human reviewers can audit the judge's logic
- Deduplication notes explain conflict resolutions

### Judge Configuration Profiles

Judges can be configured with different matching strictness:

**Strict Matching:**
```json
{
  "numeric_tolerance_percent": 0.0,
  "case_insensitive_strings": false,
  "ignore_minor_wording_diffs": false,
  "require_all_fields_match": true,
  "allow_partial_matches": false
}
```

**Lenient Matching:**
```json
{
  "numeric_tolerance_percent": 5.0,
  "case_insensitive_strings": true,
  "ignore_minor_wording_diffs": true,
  "require_all_fields_match": false,
  "allow_partial_matches": true
}
```

This allows testing: "Would this extraction be good enough for production use with human review?"
