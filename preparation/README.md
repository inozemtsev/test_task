# Synthetic Financial Transcript Generation

This repository contains scripts for generating synthetic financial advisor fact-find transcripts using OpenAI's GPT-5 API. The process ensures high-quality, structured data suitable for training and evaluation purposes.

## Overview

The synthetic transcript generation process consists of three main stages:

1. **Schema Validation** - Testing and refining the JSON schema for structured output
2. **Prompt Generation** - Creating diverse, persona-based prompts for different financial topics
3. **Transcript Generation** - Producing complete, realistic financial advisor conversations

## Project Structure

```
preparation/
├── README.md                               # This file
├── requirements.txt                        # Python dependencies
├── run.py                                  # Stage 1: Schema testing with GPT-5
├── combine_schema_examples.py              # Stage 1: Combine schema with examples
├── analyze_schema_stability.py             # Stage 1: Analyze schema consistency
├── generate_transcript_prompts.py          # Stage 2: Generate prompts
├── generate_transcripts.py                 # Stage 3: Generate transcripts
├── start/                                  # Initial templates and schemas
│   ├── schema.json                        # Original schema
│   ├── schema2.json                       # Refined schema
│   ├── synthetic_transcript1.txt          # Template transcript 1
│   ├── synthetic_transcript2.txt          # Template transcript 2
│   └── structured_result*.json            # Schema test results
├── best/                                   # Best practice examples
│   ├── res1.json                          # Example structured output 1
│   └── res2.json                          # Example structured output 2
└── prompts/                                # Generated prompts by persona
    ├── _summary.json                      # Metadata about all personas
    └── {persona_id}/                      # One folder per persona
        ├── clients.txt                    # Client information prompts
        ├── assets.txt                     # Asset discussion prompts
        ├── pensions.txt                   # Pension discussion prompts
        ├── incomes.txt                    # Income discussion prompts
        ├── expenses.txt                   # Expense discussion prompts
        ├── loans-and-mortgages.txt        # Loan discussion prompts
        └── savings-and-investments.txt    # Savings discussion prompts
```

## Installation

1. Clone or navigate to this directory:
```bash
cd /home/igor/test_task/preparation
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

## Stage 1: Schema Development and Validation

The first stage focuses on creating a stable JSON schema that works consistently across different transcript formats.

### Goal

Create a structured output schema that is:
- Neither too loose (allowing inconsistent outputs)
- Nor too strict (causing model failures)
- Stable across different input formats

### Scripts

#### 1. Testing Schema with Transcripts

Test your schema against template transcripts:

```bash
python run.py \
  --transcript_file start/synthetic_transcript1.txt \
  --schema_file start/schema2.json \
  --output_file best/res1.json
```

**Parameters:**
- `--transcript_file`: Path to the input transcript file
- `--schema_file`: Path to your JSON schema
- `--output_file`: Where to save the structured result

This script calls GPT-5 with structured output mode, applying your schema to extract structured data from the transcript.

#### 2. Combining Schema with Examples

After generating multiple structured outputs for both input transcripts with relatively loose schema, combine them to analyze field coverage:

```bash
python combine_schema_examples.py
```

**What it does:**
- Extracts all enum values from the schema
- Extracts all actual values from structured result files
- Maps schema paths to data paths
- Creates a comprehensive report showing:
  - Which fields appear in which files
  - Example values for each field
  - Citation examples with timestamps
  - Coverage statistics

**Output files:**
- `combined_schema_examples_2.json` - Combined data in JSON format
- `combined_schema_examples_report.txt` - Human-readable analysis report

#### 3. Analyzing Schema Stability

Identify potential issues and inconsistencies in your schema:

```bash
python analyze_schema_stability.py
```

**What it analyzes:**
- **Duplicate fields**: Similar field names that might represent the same concept
- **Semantic groupings**: Fields that measure related concepts
- **Structural complexity**: Nesting depth and complexity issues
- **Recommendations**: Prioritized suggestions for schema improvements

This analysis helps you identify:
- Fields that only appear in one transcript (potential schema incompleteness)
- Similar fields with different names (potential redundancy)
- Areas where the schema needs refinement

## Stage 2: Prompt Generation

The second stage creates diverse, detailed prompts for generating transcript chunks.

### Goal

Generate comprehensive prompts that:
- Cover 17 different client persona types (young couples, pre-retirees, high earners, etc.)
- Include multiple instances of each persona type (for diversity)
- Provide specific examples and guidance for each financial topic
- Include realistic attribute values and citation examples

### Running Prompt Generation

```bash
python generate_transcript_prompts.py
```

**What it does:**

1. **Loads combined schema examples** from Stage 1
2. **Generates diverse client personas** (17 types × 2 instances = 34 personas)
   - Young Professional Couple
   - Single Young Professional
   - Cohabiting Couple
   - Mid-Career Couple
   - Pre-Retirement Couple
   - Early Retirement Seeker
   - Recently Retired Couple
   - Empty Nest Couple
   - Self-Employed Business Owner
   - Blended Family
   - Career Transition Individual
   - Divorced Single Parent
   - Recent Inheritance Recipient
   - High-Earning Professionals
   - Semi-Retired Professional
   - Widowed Individual
   - First-Time Homebuyer

3. **Creates prompts for 7 financial topics**:
   - Clients (basic information)
   - Assets
   - Pensions
   - Incomes
   - Expenses
   - Loans and Mortgages
   - Savings and Investments

4. **Each prompt includes**:
   - Client case description with age, marital status, life stage
   - Focus area for the conversation segment
   - Attributes to cover with example values
   - Citation examples with timestamps
   - Timeline guidance for natural conversation flow
   - Output requirements and formatting instructions

**Output:**
- Creates `prompts/{persona_id}/` directories
- 7 prompt files per persona (one per topic)
- `_summary.json` with metadata about all personas
- Total: 34 personas × 238 topics = 714 prompts

## Stage 3: Transcript Generation

The final stage uses the prompts to generate complete, realistic transcripts.

### Goal

Generate synthetic transcripts that:
- Sound natural and realistic
- Include specific financial details and numbers
- Have proper timestamps and speaker labels
- Cover all relevant financial topics
- Feel like one continuous conversation (not rigid sections)

### Running Transcript Generation

#### Generate a Single Transcript

For testing or generating one specific persona:

```bash
python generate_transcripts.py --persona young_couple_01_john_patricia
```

#### Generate Multiple Transcripts (Batch Mode)

To generate transcripts for multiple personas in parallel:

```bash
python generate_transcripts.py --max 10 --workers 4
```

Use temperature = 1 in OpenAI API calls.

**Parameters:**
- `--prompts-dir`: Directory containing prompt subdirectories (default: `/home/igor/test_task/prompts`)
- `--output-dir`: Directory to save transcripts (default: `/home/igor/test_task/transcripts`)
- `--persona`: Generate for a specific persona only
- `--max`: Maximum number of transcripts to generate
- `--model`: OpenAI model to use (default: `gpt-5.1`)
- `--workers`: Number of parallel workers (default: CPU count)
- `--overwrite`: Overwrite existing transcripts (default: skip existing)

### How It Works

For each persona:

1. **Reads all 7 prompt files** from the persona directory
2. **Generates individual chunks** by calling OpenAI API with each prompt
3. **Combines and shuffles chunks** using a second API call to:
   - Merge all sections into one cohesive conversation
   - Shuffle topics naturally (not in rigid order)
   - Remove redundant content (10-20%)
   - Ensure natural flow and transitions
   - Maintain timestamps and speaker consistency
4. **Saves the complete transcript** with metadata header

### Output Format

Each transcript includes:
- **Metadata header**: Persona name, type, generation timestamp, temperature
- **Conversation**: Natural dialogue with timestamps `[HH:MM:SS]`
- **Speaker labels**: `ADVISOR:`, `CLIENT:`, `CLIENT1:`, `CLIENT2:`

## Complete Workflow Example

Here's a complete example of running all stages:

```bash
# Stage 1: Test schema and analyze stability
cd /home/igor/test_task/preparation

# Test schema with transcript 1
python run.py \
  --transcript_file start/synthetic_transcript1.txt \
  --schema_file start/schema2.json \
  --output_file best/res1.json

# Test schema with transcript 2
python run.py \
  --transcript_file start/synthetic_transcript2.txt \
  --schema_file start/schema2.json \
  --output_file best/res2.json

# Combine results and analyze
python combine_schema_examples.py
python analyze_schema_stability.py

# Review outputs and refine schema if needed
# Then proceed to Stage 2

# Stage 2: Generate prompts
python generate_transcript_prompts.py

# Stage 3: Generate transcripts
# Start with a small batch for testing
python generate_transcripts.py --max 1

# Then generate full batch with parallel processing
python generate_transcripts.py --workers 4
```

## Adding New Persona Types

Edit `generate_transcript_prompts.py` and add entries to the `persona_types` list:

```python
{
    'type_id': 'new_type',
    'type_name': 'New Persona Type',
    'base_description': 'Description of the persona...',
    'age_range': (30, 40),
    'marital_status': 'married',
    'employment': 'employed',
    'life_stage': 'mid-career',
    'variations': [
        'Variation 1 description',
        'Variation 2 description',
    ]
}
```

## Adding New Financial Topics

1. Update your schema to include the new topic
2. Ensure example transcripts cover this topic
3. Run Stage 1 to validate
4. Update `main_parts` list in `generate_transcript_prompts.py`:
   ```python
   main_parts = ['clients[]', 'assets[]', 'pensions[]', 'incomes[]', 
                 'expenses[]', 'loans_and_mortgages[]', 
                 'savings_and_investments[]', 'new_topic[]']
   ```

## Customizing Generation Behavior

Edit system prompts in `generate_transcripts.py`:
- `generate_chunk()` method: Controls individual chunk generation
- `combine_and_shuffle()` method: Controls final transcript assembly

