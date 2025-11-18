# Claude Code Agent Session Summary

This document summarizes the features and fixes implemented during the Claude Code agent session.

## Features Implemented

### 1. Selective Transcript Evaluation
**Description:** Added ability to run evaluations on selected transcripts instead of all transcripts.

**Backend Changes:**
- **`schemas.py`**: Added optional `transcript_ids: list[int]` field to `EvaluationRunRequest`
- **`services/evaluation_service.py`**: Updated `run_evaluation()` to accept and filter by `transcript_ids`
  - Uses `Transcript.id.in_(transcript_ids)` when IDs provided
  - Falls back to all transcripts if None
- **`routers/evaluations.py`**: Passes `transcript_ids` from request to service

**Frontend Changes:**
- **`components/EvaluationRunner.tsx`**:
  - Added transcript selection UI with checkboxes
  - "Select All" and "Clear" buttons
  - Shows count of selected transcripts
  - ScrollArea with 200px height for transcript list
  - Sends `transcript_ids` array to backend (or undefined for all)

### 2. Detailed Evaluation Results Viewer
**Description:** Added comprehensive view of evaluation results showing transcript-level details.

**New Component:**
- **`components/EvaluationResultsViewer.tsx`**:
  - Accordion-based UI showing each evaluated transcript
  - Displays extracted data in scrollable JSON view
  - Shows characteristic evaluations with pass/fail badges
  - Includes reasoning for each characteristic vote
  - Shows overall pass percentage per transcript

**Integration:**
- **`components/Leaderboard.tsx`**:
  - Added "View" button with Eye icon for each evaluation
  - Opens dialog with `EvaluationResultsViewer`
  - Dialog is full-width (max-w-4xl) with vertical scroll

### 3. Leaderboard Moved to Judges
**Description:** Moved leaderboard from experiments to judges, showing which experiments performed best under each judge.

**Backend Changes:**
- **`routers/judges.py`**:
  - Added `GET /api/judges/{judge_id}/leaderboard` endpoint
  - Returns experiments ranked by average score for that judge
  - Uses same `LeaderboardEntry` schema as before

**Frontend Changes:**
- **`lib/api.ts`**: Added `judgesAPI.getLeaderboard(judgeId)` method
- **`components/JudgeDetail.tsx`**:
  - Added tabs for "Characteristics" and "Leaderboard"
  - Integrated `Leaderboard` component in judge detail view
  - Auto-refreshes every 5 seconds
- **`components/ExperimentDetail.tsx`**:
  - Removed leaderboard tab (now only shows configuration details)
  - Simplified to single card view without tabs

## Bugs Fixed

### 1. CORS Issues
**Problem:** CORS errors when running evaluations from frontend.

**Fix:**
- **`routers/evaluations.py`**: Added explicit CORS headers to SSE streaming endpoint:
  ```python
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "*"
  ```

### 2. OpenAI Function Calling Schema Format
**Problem:** Schema validation errors when using OpenAI function calling API.

**Root Cause:** Schemas in database had structured outputs format `{name, strict, schema}` but function calling needs the inner schema object.

**Fix:**
- **`services/llm_service.py`**:
  - Updated `extract_structured_data()` to match `run.py` pattern
  - Uses `response_format={"type": "json_object"}` with `tool_choice="auto"`
  - Extracts response from `tool_calls[0].function.arguments` with fallback to `message.content`
  - Validates schema is dict before passing to function parameters
  - Falls back to default schema if custom schema is invalid

### 3. Invalid Schema Handling
**Problem:** Characteristics without valid schemas caused "got 'type: "None"'" errors.

**Fix:**
- **`services/llm_service.py`**:
  - Added validation to check if schema exists, is not empty, and has `"type"` field
  - Falls back to default boolean pass/fail schema if invalid
  - Default schema includes `passes` (boolean) and `reasoning` (string)

### 4. SQLAlchemy Async Relationship Loading Errors
**Problem:** Multiple `MissingGreenlet` errors when accessing relationships in async endpoints.

**Occurrences:**
1. Judge creation/update endpoints
2. Evaluation run endpoint
3. Evaluation get endpoint

**Fix Pattern:** Pre-load all relationships with `selectinload()` before returning responses:

**`routers/evaluations.py`**:
```python
# In start_evaluation:
result = await db.execute(
    select(Evaluation)
    .options(
        selectinload(Evaluation.results)
        .selectinload(EvaluationResult.characteristic_votes)
    )
    .where(Evaluation.id == evaluation.id)
)

# In get_evaluation:
result = await db.execute(
    select(Evaluation)
    .options(
        selectinload(Evaluation.results)
        .selectinload(EvaluationResult.transcript),
        selectinload(Evaluation.results)
        .selectinload(EvaluationResult.characteristic_votes)
        .selectinload(CharacteristicVote.characteristic)
    )
    .where(Evaluation.id == evaluation_id)
)
```

### 5. Delete Characteristic API Mismatch
**Problem:** Frontend calling wrong endpoint path for deleting characteristics.

**Fix:**
- **`lib/api.ts`**: Changed from `/api/characteristics/{id}` to `/api/judges/characteristics/{id}` to match backend router prefix

### 6. JSON Schema Editor Formatting
**Problem:** Schemas loaded as single line in Monaco editor when editing experiments.

**Fix:**
- **`components/JSONSchemaEditor.tsx`**: Added `onMount` handler to auto-format document:
  ```typescript
  onMount={(editor) => {
    setTimeout(() => {
      editor.getAction('editor.action.formatDocument')?.run();
    }, 100);
  }}
  ```

### 7. Schema Display in View Mode
**Problem:** Schema showing collapsed in experiment detail view.

**Fix:**
- **`components/ExperimentDetail.tsx`**: Changed `whitespace-pre-wrap` to `whitespace-pre` and added `overflow-auto` for proper formatting

### 8. Empty Schema Validation
**Problem:** Empty string schemas causing JSON parse errors.

**Fix:**
- **`routers/judges.py`**: Added type and content validation:
  ```python
  if characteristic_data.schema_json:
      if isinstance(characteristic_data.schema_json, str) and characteristic_data.schema_json.strip():
          json.loads(characteristic_data.schema_json)  # Validate
      else:
          characteristic_data.schema_json = None  # Normalize empty to None
  ```

## API Changes

### New Endpoints
- `GET /api/judges/{judge_id}/leaderboard` - Get experiments ranked by score for a judge

### Modified Endpoints
- `POST /api/evaluations/run` - Now accepts optional `transcript_ids: list[int]` parameter

### Removed Endpoints
- None (backward compatible)

## Database Schema
No changes to database schema. All changes were backward compatible.

## Frontend Dependencies
- Added `@/components/ui/accordion` (shadcn/ui component)

## Key Patterns Established

### 1. SQLAlchemy Async Relationships
Always use `selectinload()` to pre-load relationships in async endpoints before serializing with Pydantic:
```python
result = await db.execute(
    select(Model)
    .options(selectinload(Model.relationship))
    .where(Model.id == id)
)
```

### 2. OpenAI Function Calling
Use the pattern from `run.py`:
- `response_format={"type": "json_object"}`
- `tool_choice="auto"`
- Schema passed directly to `function.parameters`
- Extract from `tool_calls[0].function.arguments` with fallback

### 3. Optional Schema Validation
Always validate optional schemas are non-empty strings before parsing:
```python
if schema_json:
    if isinstance(schema_json, str) and schema_json.strip():
        schema = json.loads(schema_json)
        # Use schema
    else:
        # Use default or None
```

## Testing Recommendations
1. Test evaluation with no transcripts selected (should run all)
2. Test evaluation with subset of transcripts selected
3. Test viewing evaluation details with multiple transcripts
4. Test judge leaderboard with multiple evaluations
5. Test creating characteristics with and without schemas
6. Test editing experiments with malformed JSON schemas

## Known Limitations
- Leaderboard refreshes every 5 seconds (not real-time)
- No pagination for large numbers of transcripts in evaluation results
- No search/filter in transcript selection UI

---

# Session 2: Enhanced Metrics & Schema Validation System

## Features Implemented

### 1. Advanced Evaluation Metrics with Numerator/Denominator Support
**Description:** Extended the metrics system to support both simple float values and complex numerator/denominator pairs for precise accuracy tracking.

**Backend Changes:**
- **`models.py`**:
  - Added `metrics` (JSON) column to `CharacteristicVote` - stores per-characteristic metrics
  - Added `schema_overlap_percentage` (FLOAT) to `EvaluationResult` - tracks schema coverage
  - Added `result_data` (JSON) to `CharacteristicVote` - stores complete LLM response with all custom fields

- **`schemas.py`**:
  - Updated `CharacteristicVoteResponse.metrics` to `dict[str, Any]` (supports both float and object types)
  - Added `result_data: Optional[dict[str, Any]]` to store full evaluation response
  - Updated `LeaderboardEntry` with:
    - `avg_schema_overlap: Optional[float]` - average schema coverage
    - `avg_metrics: Optional[dict[str, Any]]` - aggregated metrics (handles numerator/denominator)
    - `characteristic_results: Optional[dict[str, Any]]` - per-characteristic aggregated data

- **`services/llm_service.py`**:
  - Implemented `flatten_dict_keys()` - recursively flattens nested dictionaries
  - Implemented `get_schema_fields()` - extracts all field paths from JSON schema
  - Implemented `calculate_schema_overlap()` - calculates percentage of schema fields present in extracted data
  - Updated `evaluate_characteristic()` return type: `tuple[bool, str, dict[str, float], dict]`
    - Now returns: (vote, reasoning, metrics, full_result_data)
  - Updated default schema to request optional `metrics` field alongside passes/reasoning

- **`services/evaluation_service.py`**:
  - Integrated `calculate_schema_overlap()` after data extraction
  - Stores full `result_data` in CharacteristicVote for custom field display

- **`routers/judges.py` & `routers/experiments.py`**:
  - Enhanced leaderboard aggregation with intelligent metric handling:
    - **Numerator/Denominator**: Sums numerators and denominators separately (e.g., 5/10 + 3/8 = 8/18)
    - **Regular floats**: Averages normally
  - Added `characteristic_results` aggregation showing per-characteristic:
    - Pass/fail counts
    - Aggregated metrics (summed or averaged based on type)
  - Pre-loads characteristic relationships for proper name display

**Frontend Changes:**
- **`components/Leaderboard.tsx`**:
  - **Removed** "pass rate" column (avg_score display)
  - **Added** schema coverage display with blue highlighting
  - **Added** per-characteristic results showing:
    - Pass/fail ratio when no metrics (e.g., "15/20")
    - Numerator/denominator with percentage (e.g., "assets_found: 45/60 (75.0%)")
    - Regular metrics as percentages (e.g., "accuracy: 85%")
  - Organized by characteristic name for clarity

- **`components/EvaluationResultsViewer.tsx`**:
  - Added schema coverage badge in accordion trigger
  - Added Schema Coverage section with progress bar
  - **Dynamic field rendering** from `result_data`:
    - Reasoning: Multiline text formatting
    - Metrics: Numerator/denominator or percentage display
    - Arrays: Bulleted lists
    - Objects: Formatted JSON in code blocks
    - Primitives: Key-value pairs
  - Backwards compatible: Falls back to individual fields (reasoning, metrics) for old evaluations

**Database Migration:**
- Manual column additions via SQLite ALTER TABLE:
  ```sql
  ALTER TABLE evaluation_results ADD COLUMN schema_overlap_percentage REAL;
  ALTER TABLE characteristic_votes ADD COLUMN metrics TEXT;
  ALTER TABLE characteristic_votes ADD COLUMN result_data TEXT;
  ```

**Example Schema with Custom Fields:**
```json
{
  "type": "object",
  "properties": {
    "passes": {"type": "boolean"},
    "reasoning": {"type": "string"},
    "metrics": {
      "type": "object",
      "properties": {
        "assets_found": {
          "type": "object",
          "properties": {
            "numerator": {"type": "number"},
            "denominator": {"type": "number"}
          }
        }
      }
    },
    "confidence": {"type": "number"},
    "issues_found": {"type": "array", "items": {"type": "string"}},
    "recommendations": {"type": "string"}
  },
  "required": ["passes", "reasoning"]
}
```

## Bugs Fixed

### 1. Database Schema Migration
**Problem:** `OperationalError: no such column: evaluation_results.schema_overlap_percentage`

**Root Cause:** SQLite doesn't auto-add columns when models change.

**Fix:**
- Added columns manually using SQLite ALTER TABLE commands
- Verified schema with `PRAGMA table_info()`

### 2. Database Locking Issues
**Problem:** `sqlite3.OperationalError: database is locked` when deleting characteristics.

**Root Cause:** Multiple backend processes or stuck transactions holding database locks.

**Fix:**
- Identified running processes with `ps aux | grep python.*main.py`
- Killed stuck processes
- Verified database unlock with `fuser app.db`
- Recommended running only one backend instance at a time

### 3. Characteristic Delete Cascade Failure
**Problem:** `IntegrityError: NOT NULL constraint failed: characteristic_votes.characteristic_id`

**Root Cause:** SQLAlchemy trying to SET NULL instead of CASCADE DELETE on CharacteristicVote records.

**Fix:**
- **`models.py`**: Added `cascade="all, delete-orphan"` to `Characteristic.votes` relationship
- **`routers/judges.py`**: Updated delete endpoint to pre-load votes with `selectinload(Characteristic.votes)`
- Ensures proper cascade deletion in async context

## API Changes

### Modified Endpoints
- `GET /api/judges/{judge_id}/leaderboard` - Now returns `characteristic_results` with per-test aggregated data
- `GET /api/experiments/{experiment_id}/leaderboard` - Now returns `characteristic_results` with per-test aggregated data

### Response Schema Changes
All changes are backwards compatible with optional fields:
- `LeaderboardEntry` now includes `avg_schema_overlap`, `avg_metrics`, `characteristic_results`
- `CharacteristicVoteResponse` now includes `result_data` with full LLM response
- `EvaluationResultResponse` now includes `schema_overlap_percentage`

## Database Schema Changes

### New Columns
1. `evaluation_results.schema_overlap_percentage` (REAL, nullable)
2. `characteristic_votes.metrics` (TEXT/JSON, nullable)
3. `characteristic_votes.result_data` (TEXT/JSON, nullable)

### Relationship Updates
- `Characteristic.votes` - Added cascade="all, delete-orphan"

## Key Patterns Established

### 1. Numerator/Denominator Aggregation
When aggregating metrics across transcripts:
```python
# CORRECT: Sum numerators and denominators separately
total_numerator = sum(v["numerator"] for v in values)
total_denominator = sum(v["denominator"] for v in values)
result = {"numerator": total_numerator, "denominator": total_denominator}

# WRONG: Average of ratios
avg = sum(v["numerator"]/v["denominator"] for v in values) / len(values)
```

### 2. Schema Overlap Calculation
```python
# Flatten both schema and extracted data
schema_fields = get_schema_fields(schema)  # e.g., {'clients.name', 'clients.age'}
extracted_fields = flatten_dict_keys(data)  # e.g., {'clients.name'}
overlap = len(schema_fields & extracted_fields) / len(schema_fields)
```

### 3. Dynamic Field Rendering
Frontend should handle multiple data types from `result_data`:
- Check type with `typeof value` and `Array.isArray(value)`
- Special handling for `reasoning` (multiline), `metrics` (numerator/denominator), and `passes` (badge)
- Fall back to JSON.stringify for complex objects

### 4. Cascade Delete Pattern
For proper cascade deletion in async SQLAlchemy:
```python
# In model
votes = relationship("CharacteristicVote", cascade="all, delete-orphan")

# In delete endpoint
result = await db.execute(
    select(Characteristic)
    .options(selectinload(Characteristic.votes))
    .where(Characteristic.id == id)
)
await db.delete(characteristic)
await db.commit()
```

## Frontend Dependencies
- Added `@/components/ui/progress` (shadcn/ui component) for schema coverage display

## Testing Recommendations
1. **Numerator/Denominator Metrics**:
   - Create characteristic with numerator/denominator schema
   - Run evaluation on multiple transcripts
   - Verify leaderboard shows summed values (not averaged ratios)
   - Example: 5/10 + 3/8 should show 8/18 (44.4%), not 40.6%

2. **Schema Overlap**:
   - Create experiment with comprehensive schema
   - Ensure extracted data has partial coverage
   - Verify percentage shown on leaderboard and results viewer
   - Check progress bar visual representation

3. **Custom Fields**:
   - Add custom fields to characteristic schema (confidence, issues_found, etc.)
   - Run new evaluation
   - Verify all custom fields displayed in results viewer
   - Test arrays, objects, and primitive types

4. **Cascade Delete**:
   - Create characteristic with associated votes (run evaluation)
   - Delete characteristic
   - Verify no integrity errors
   - Check votes are deleted from database

5. **Backwards Compatibility**:
   - View old evaluations (without result_data)
   - Verify reasoning and metrics still display
   - Ensure no errors with null/undefined fields

## Performance Considerations
- Leaderboard aggregation now performs additional queries to fetch and aggregate metrics
- Each leaderboard entry requires loading all characteristic votes
- For evaluations with many transcripts/characteristics, consider caching or pagination

## Migration Notes
- **Manual database updates required** for existing deployments
- Run ALTER TABLE commands before deploying new backend code
- Old evaluations will have NULL for new fields (handled gracefully by frontend)
- No data loss - all existing data preserved

## Known Issues & Limitations
- Schema overlap only counts exact key matches (doesn't validate data types or values)
- Leaderboard aggregation can be slow with many transcripts
- No UI for configuring which metrics to display on leaderboard
- Numerator/denominator assumes all values in a metric are the same type (all objects or all floats)

---

# Session 3: Performance Optimization & Two-Pass Extraction

## Features Implemented

### 1. Parallel Transcript Processing with Multiprocessing
**Description:** Implemented multiprocessing to parallelize transcript evaluation, enabling ~N× speedup where N = CPU cores.

**Architecture:**
- **Worker processes**: Each transcript is processed completely (extraction + characteristic evaluations) on a dedicated CPU core
- **Result collection**: Workers return serialized results to main process
- **Database writes**: Main process handles all SQLite writes sequentially (avoids concurrent write issues)

**Backend Changes:**
- **`services/evaluation_service.py`**:
  - Added `_async_process_transcript()` - Async function that processes one transcript without DB operations
    - Performs extraction (with optional two-pass)
    - Evaluates all characteristics
    - Returns complete results as serializable dict
  - Added `process_transcript_worker()` - Sync wrapper that creates event loop for worker process
  - Modified `run_evaluation()` to use `ProcessPoolExecutor`:
    - Worker pool size: `min(cpu_count, num_transcripts)`
    - Submits all transcript jobs in parallel
    - Collects results using `asyncio.as_completed()`
    - Writes all results to DB sequentially after executor closes
    - Real-time progress tracking as results complete

**Key Implementation Details:**
```python
# Process transcripts in parallel
max_workers = min(os.cpu_count() or 1, len(transcripts))
with ProcessPoolExecutor(max_workers=max_workers) as executor:
    futures = [
        loop.run_in_executor(executor, process_transcript_worker, ...)
        for transcript in transcripts
    ]
    # Collect results as they complete
    for future in asyncio.as_completed(futures):
        result = await future
        all_results.append(result)

# Write to DB after executor closed
for result in all_results:
    # Create EvaluationResult and CharacteristicVote records
```

**Benefits:**
- ~N× speedup (parallelizes slow LLM API calls)
- SQLite-safe (sequential database writes)
- Better error isolation (worker crash doesn't affect others)
- Real-time progress updates

### 2. Two-Pass Extraction with Review Step
**Description:** Optional feature that adds a review step between initial extraction and final output, improving extraction quality.

**Extraction Flow:**
1. **First Pass**: Standard structured data extraction
2. **Review**: LLM analyzes transcript + extraction, identifies missing or hallucinated items
3. **Second Pass**: Re-extracts with review feedback to produce refined output

**Backend Changes:**
- **`models.py`**:
  - Added `enable_two_pass` (BOOLEAN) to `Experiment` model
  - Added three new columns to `EvaluationResult`:
    - `initial_extraction` (TEXT/JSON) - first pass output
    - `review_data` (TEXT/JSON) - review findings
    - `final_extraction` (TEXT/JSON) - second pass output

- **`schemas.py`**:
  - Added `enable_two_pass: bool = False` to `ExperimentBase`
  - Added `enable_two_pass: Optional[bool] = None` to `ExperimentUpdate`

- **`services/llm_service.py`**:
  - Implemented `review_extraction()`:
    - Takes transcript, initial extraction, and schema
    - Returns standardized review with: `missing_items`, `hallucinated_items`, `other_issues`
    - Uses fixed default review prompt for consistency
  - Implemented `extract_with_review()`:
    - Takes all parameters from first pass + review data
    - Re-extracts with review context
    - Returns refined extraction

- **`services/evaluation_service.py`**:
  - Integrated two-pass logic in `_async_process_transcript()`:
    - Checks `experiment.enable_two_pass` flag
    - Stores all three artifacts (initial, review, final)
    - Uses final extraction for characteristic evaluation

- **`routers/experiments.py`**:
  - Added `enable_two_pass` field handling in create and update endpoints

**Frontend Changes:**
- **`lib/api.ts`**: Added `enable_two_pass?: boolean` to experiment types
- **`components/ExperimentForm.tsx`**: Added two-pass toggle with explanation
- **`components/ExperimentEditForm.tsx`**: Added two-pass toggle
- **`components/ExperimentDetail.tsx`**: Shows badge when two-pass enabled
- **`components/EvaluationResultsViewer.tsx`**: Added comprehensive review findings display:
  - Summary section
  - Missing items (amber styling)
  - Hallucinated items (red styling)
  - Other issues (blue styling)

**Database Migration:**
```sql
ALTER TABLE experiments ADD COLUMN enable_two_pass INTEGER DEFAULT 0;
ALTER TABLE evaluation_results ADD COLUMN initial_extraction TEXT;
ALTER TABLE evaluation_results ADD COLUMN review_data TEXT;
ALTER TABLE evaluation_results ADD COLUMN final_extraction TEXT;
```

### 3. Schema Stability Metric (Renamed from Schema Coverage)
**Description:** Changed per-transcript schema coverage to per-evaluation schema stability, measuring consistency of extracted fields across all transcripts.

**Conceptual Change:**
- **OLD**: Per-transcript metric = (fields in extraction / schema fields), averaged
- **NEW**: Per-evaluation metric = (common fields in ALL transcripts / total unique fields across ALL transcripts)

**Example:**
```
Transcript 1: {name, age, city}
Transcript 2: {name, age, country}
Transcript 3: {name, age, city}

Common fields: {name, age} = 2
Total unique: {name, age, city, country} = 4
Stability: 2/4 = 50%
```

**Backend Changes:**
- **`models.py`**:
  - Removed `schema_overlap_percentage` from `EvaluationResult` (per-transcript)
  - Added `schema_stability` (FLOAT) to `Evaluation` model (per-evaluation)

- **`schemas.py`**:
  - Removed `schema_overlap_percentage` from `EvaluationResultResponse`
  - Added `schema_stability: Optional[float]` to `EvaluationResponse`
  - Updated `LeaderboardEntry.avg_schema_overlap` → `schema_stability`

- **`services/llm_service.py`**:
  - `calculate_schema_stability()` now works correctly:
    - Flattens extracted data from all transcripts
    - Calculates intersection (common fields) and union (total unique fields)
    - Returns stability ratio
  - `flatten_dict_keys()` properly handles:
    - Nested dictionaries
    - Arrays (marked with `[]` notation)
    - Primitive values in arrays
  - Removed unused `calculate_schema_overlap()` and `get_schema_fields()` functions
  - Removed debug print statements

- **`services/evaluation_service.py`**:
  - Collects `all_extracted_data` from all transcripts
  - Calculates `schema_stability` once after all processing complete
  - Stores on `evaluation` object

- **`routers/judges.py` & `routers/experiments.py`**:
  - Updated leaderboard queries to include `Evaluation.schema_stability`
  - Direct value access (no longer averaging per-transcript values)

**Frontend Changes:**
- **`components/Leaderboard.tsx`**: Changed display from `avg_schema_overlap` to `schema_stability`
- **`components/EvaluationResultsViewer.tsx`**: Removed per-result stability, added overall stability badge

**Database Migration:**
```sql
ALTER TABLE evaluations ADD COLUMN schema_stability REAL;
```

### 4. Default Schema Enhancement
**Description:** Moved numerator/denominator fields to top level of default evaluation schema alongside passes and reasoning.

**Schema Structure:**
```json
{
  "type": "object",
  "properties": {
    "passes": {"type": "boolean"},
    "numerator": {"type": "number"},
    "denominator": {"type": "number"},
    "reasoning": {"type": "string"},
    "metrics": {"type": "object"}
  },
  "required": ["passes", "reasoning"]
}
```

**Backend Changes:**
- **`services/llm_service.py`**: Updated default schema in `evaluate_characteristic()`

**Frontend Changes:**
- **`components/EvaluationResultsViewer.tsx`**: Added display for top-level numerator/denominator

## Bugs Fixed

### 1. SQLAlchemy Transaction State Error (Background Task + DB Session)
**Problem:** `IllegalStateChangeError: Method 'close()' can't be called here; method '_connection_for_bind()' is already in progress`

**Root Cause:**
- `run_evaluation()` called as background task via `asyncio.create_task()`
- Received database session from request's dependency injection
- When request returned, `get_db()` tried to close session
- But background task still using session → transaction state conflict

**Fix:**
- **`services/evaluation_service.py`**:
  - Removed `db: AsyncSession` parameter from `run_evaluation()`
  - Added `from database import AsyncSessionLocal`
  - Wrapped function body in `async with AsyncSessionLocal() as db:`
  - Background task now creates its own independent session

- **`routers/evaluations.py`**:
  - Changed: `asyncio.create_task(run_evaluation(evaluation.id, db, ...))`
  - To: `asyncio.create_task(run_evaluation(evaluation.id, ...))`
  - No longer passes request's session to background task

**Result:** Clean separation of session lifecycles - no conflicts

### 2. ProcessPoolExecutor Transaction Conflicts
**Problem:** Same `IllegalStateChangeError` even after implementing multiprocessing

**Root Cause:**
- Database commits happening inside `ProcessPoolExecutor` context
- While `asyncio.as_completed()` awaiting futures
- Created conflicting transaction states

**Fix:**
- **`services/evaluation_service.py`**:
  - Separated result collection from database writes:
    1. Collect all results into memory (inside executor context)
    2. Exit executor context cleanly
    3. Write all results to database sequentially (outside executor context)
  - Added progress message: "Writing results to database..."

**Result:** Clean separation of parallel processing and database operations

### 3. Missing Two-Pass Toggle in Edit Form
**Problem:** Two-pass toggle not visible when editing experiments

**Fix:** Added identical toggle UI to `ExperimentEditForm.tsx`

### 4. enable_two_pass Not Persisting on Update
**Problem:** Two-pass setting not saved when clicking "Save Changes"

**Fix:**
- **`routers/experiments.py`**: Added field handling in `update_experiment()`:
```python
if experiment_data.enable_two_pass is not None:
    experiment.enable_two_pass = experiment_data.enable_two_pass
```

## API Changes

### Modified Endpoints
- `POST /api/evaluations/run` - No longer requires `db` parameter (handled internally)
- `PUT /api/experiments/{id}` - Now handles `enable_two_pass` field
- `GET /api/judges/{judge_id}/leaderboard` - Returns `schema_stability` instead of `avg_schema_overlap`
- `GET /api/experiments/{experiment_id}/leaderboard` - Returns `schema_stability` instead of `avg_schema_overlap`

### Response Schema Changes
- `EvaluationResponse`: Added `schema_stability: Optional[float]`
- `LeaderboardEntry`: Changed `avg_schema_overlap` → `schema_stability`
- `EvaluationResultResponse`: Removed `schema_overlap_percentage`

## Database Schema Changes

### New Columns
1. `experiments.enable_two_pass` (INTEGER/BOOLEAN, default 0)
2. `evaluations.schema_stability` (REAL, nullable)
3. `evaluation_results.initial_extraction` (TEXT/JSON, nullable)
4. `evaluation_results.review_data` (TEXT/JSON, nullable)
5. `evaluation_results.final_extraction` (TEXT/JSON, nullable)

### Removed Columns
- `evaluation_results.schema_overlap_percentage` (replaced with evaluation-level stability)

## Key Patterns Established

### 1. Background Task Session Management
Background tasks must create their own database sessions:
```python
async def background_task(task_id: int):
    async with AsyncSessionLocal() as db:
        # Do work with db
        await db.commit()

# In endpoint
asyncio.create_task(background_task(id))  # Don't pass request's db session!
```

### 2. Multiprocessing with AsyncIO
Pattern for parallel processing with async operations:
```python
def worker(args):
    """Sync entry point for ProcessPoolExecutor"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_worker(args))
    finally:
        loop.close()

async def async_worker(args):
    """Actual async work"""
    return await do_async_stuff(args)
```

### 3. SQLite-Safe Parallel Processing
When using multiprocessing with SQLite:
1. Workers do computation (no DB access)
2. Workers return serialized results
3. Main process writes all results sequentially
4. Avoids concurrent write issues entirely

### 4. Schema Stability Calculation
Measure field consistency across extractions:
```python
field_sets = [flatten_dict_keys(data) for data in all_extracted_data]
common = set.intersection(*field_sets)
total_unique = set.union(*field_sets)
stability = len(common) / len(total_unique)
```

### 5. Two-Pass Extraction Pattern
Standardized review schema improves consistency:
```python
{
  "missing_items": ["list of items not found"],
  "hallucinated_items": ["list of items incorrectly added"],
  "other_issues": ["list of other problems"]
}
```

## Performance Improvements
- **~N× speedup** for evaluations where N = CPU cores
- Parallelizes slow LLM API calls (the bottleneck)
- Database writes remain sequential (fast, not the bottleneck)
- Example: 8-core machine can process 8 transcripts simultaneously

## Testing Recommendations

### Multiprocessing
1. Run evaluation with 10+ transcripts
2. Verify all transcripts processed successfully
3. Check progress updates in real-time
4. Confirm no database locking errors
5. Verify schema stability calculated correctly

### Two-Pass Extraction
1. Enable two-pass on experiment
2. Run evaluation and check results viewer
3. Verify review findings displayed (missing, hallucinated, issues)
4. Compare initial vs final extraction quality
5. Test with experiment that has poor initial extraction

### Schema Stability
1. Create transcripts with varying field coverage
2. Run evaluation
3. Verify stability metric makes sense (common/total ratio)
4. Check leaderboard displays stability correctly
5. Test with deeply nested schemas and arrays

### Background Task Sessions
1. Start multiple evaluations in quick succession
2. Verify no transaction state errors
3. Check each evaluation has its own session
4. Confirm evaluations complete successfully

## Migration Notes
- **Database migrations required** before deploying
- Run all ALTER TABLE commands in sequence
- Restart backend after migration
- Old evaluations will have NULL for new fields (handled gracefully)
- Two-pass disabled by default (opt-in feature)

## Performance Considerations
- CPU-bound: Speedup scales with available cores
- Memory usage increases with worker count (limit pool size if needed)
- SQLite sequential writes not a bottleneck (LLM calls are)
- Progress tracking works in real-time across processes

## Known Limitations
- Worker pool size limited by CPU count
- No persistent worker pool (created per evaluation)
- Two-pass doubles LLM API costs
- Schema stability requires at least 2 transcripts to be meaningful
- Review findings quality depends on LLM model capability
