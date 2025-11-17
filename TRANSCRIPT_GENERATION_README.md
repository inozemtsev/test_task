# Transcript Generation Guide

## Setup

### 1. Install Dependencies
```bash
pip install openai
# or
pip install -r requirements.txt
```

### 2. Set OpenAI API Key
```bash
export OPENAI_API_KEY='your-api-key-here'
```

Or create a `.env` file:
```
OPENAI_API_KEY=your-api-key-here
```

## Usage

### Generate Transcript for ONE Person
```bash
python3 generate_transcripts.py --persona young_couple_01_daniel_mary
```

### Generate Transcripts for First 5 Personas
```bash
python3 generate_transcripts.py --max 5
```

### Generate ALL Transcripts (102 personas)
```bash
python3 generate_transcripts.py
```

### Generate with Custom Worker Count
```bash
# Use 4 parallel workers
python3 generate_transcripts.py --workers 4

# Use 8 parallel workers
python3 generate_transcripts.py --workers 8 --max 20
```

### Options
- `--prompts-dir`: Directory with prompts (default: ./prompts)
- `--output-dir`: Where to save transcripts (default: ./transcripts)
- `--persona`: Generate for specific persona only
- `--max`: Maximum number to generate
- `--model`: OpenAI model (default: gpt-5.1)
- `--overwrite`: Overwrite existing transcripts
- `--workers`: Number of parallel workers (default: CPU count)

## Multiprocessing

The script uses **multiprocessing** to generate transcripts in parallel:

- **Each worker processes 1 complete persona** (7 chunks + 1 combine call)
- **Default workers**: Uses all available CPU cores
- **Custom workers**: Use `--workers N` to control parallelism
- **Progress tracking**: Real-time updates as personas complete
- **Token aggregation**: Collects token usage from all workers

**Example Output:**
```
TRANSCRIPT GENERATION BATCH (MULTIPROCESSING)
================================================================================
Prompts directory: /home/igor/test_task/prompts
Output directory: /home/igor/test_task/transcripts
Total personas: 102
Parallel workers: 8 (each handles 1 persona at a time)
================================================================================

[1/102] ✓ young_couple_01_daniel_mary
[2/102] ✓ single_professional_01_andrew
[3/102] ○ high_earner_01_kevin_emily (skipped - already exists)
[4/102] ✗ divorced_parent_01_sarah
     └─ Error: API rate limit exceeded
...
```

**Symbols:**
- ✓ = Successfully generated
- ○ = Skipped (already exists)
- ✗ = Failed

## How It Works

For each persona (processed in parallel):

1. **Generate 7 Chunks**: Calls OpenAI API for each prompt file:
   - clients.txt → generates client details conversation
   - assets.txt → generates assets conversation
   - pensions.txt → generates pensions conversation
   - incomes.txt → generates income conversation
   - expenses.txt → generates expenses conversation
   - loans-and-mortgages.txt → generates loans conversation
   - savings-and-investments.txt → generates investments conversation

2. **Combine & Shuffle**: Calls OpenAI again with all chunks:
   - Combines all 7 chunks
   - Shuffles topics naturally
   - Removes 10-20% redundant content
   - Uses higher temperature (0.9-1.2) for variation
   - Creates one cohesive 15-25 minute conversation

3. **Save**: Saves final transcript to `transcripts/{persona_id}.txt`

## Output Structure

```
transcripts/
├── young_couple_01_daniel_mary.txt
├── single_professional_01_andrew.txt
├── high_earner_01_kevin_emily.txt
└── ... (102 transcripts total)
```

Each transcript includes:
- Metadata header (persona, type, timestamp, temperature)
- Complete shuffled conversation (15-25 minutes)
- Natural flow with interwoven topics
- Proper timestamps [HH:MM:SS]

## Cost Estimation

Using gpt-5.1:
- ~7 API calls per persona (7 chunks)
- 1 API call for combining/shuffling
- **Total: 8 API calls per transcript**
- 102 personas × 8 calls = **816 API calls total**

### Token Tracking and Pricing (gpt-5.1)

The script automatically tracks:
- Input tokens: $1.25 per 1M tokens
- Cached input tokens: $0.125 per 1M tokens (90% discount!)
- Output tokens: $10.00 per 1M tokens
- Reasoning tokens: included in output token count

Estimated cost: ~$8-15 for all 102 transcripts (with caching savings)

## Tips

- **Start small**: Use `--max 1 --workers 1` to test
- **Scale up**: Use `--max 5` for a small batch with parallel processing
- **Optimize workers**: More workers = faster, but watch API rate limits
- **Skip existing**: The script skips existing transcripts by default
- **Regenerate**: Use `--overwrite` to regenerate specific transcripts
- **Single persona**: Use `--persona NAME` for sequential processing (no multiprocessing)
- **Temperature**: Fixed at 1.0 for consistency
- **Token tracking**: Aggregates usage from all workers
- **Cost estimates**: Displayed at the end of batch generation

## Performance

**Single-threaded** (old behavior):
- 102 personas × ~8 API calls each × ~5 seconds = **~68 minutes**

**Multiprocessing** (new behavior):
- With 8 workers: **~8-10 minutes** (8x speedup)
- With 16 workers: **~4-5 minutes** (16x speedup, watch rate limits!)
