import json
from openai import AsyncOpenAI
from config import settings
from services.schema_utils import flatten_dict_keys, get_schema_fields, calculate_field_overlap

client = AsyncOpenAI(api_key=settings.openai_api_key)


async def get_available_models():
    """Fetch available models from OpenAI API"""
    try:
        models = await client.models.list()
        # Filter for relevant models (GPT-4, GPT-3.5, etc.)
        model_ids = [
            model.id
            for model in models.data
            if any(
                prefix in model.id.lower()
                for prefix in ["gpt-4", "gpt-3.5", "gpt-5"]
            )
        ]
        return sorted(model_ids)
    except Exception as e:
        # Return default models if API call fails
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]


def calculate_schema_stability(all_extracted_data: list[dict]) -> float:
    """
    Calculate schema stability across multiple extractions.
    Measures field consistency: (common fields) / (total unique fields)

    Args:
        all_extracted_data: List of extracted data dicts from all transcripts

    Returns:
        float: Stability score between 0.0 (no common fields) and 1.0 (all same fields)

    Example:
        Transcript 1: {name, age, city}
        Transcript 2: {name, age, country}
        Transcript 3: {name, age, city}
        Common: {name, age} = 2
        Total unique: {name, age, city, country} = 4
        Stability: 2/4 = 0.5 (50%)
    """
    if not all_extracted_data or len(all_extracted_data) == 0:
        return 0.0

    try:
        # Get field sets for each extraction (flatten nested dicts)
        field_sets = [flatten_dict_keys(data) for data in all_extracted_data]

        # Filter out empty sets
        field_sets = [fs for fs in field_sets if fs]

        if not field_sets:
            return 0.0

        # Common fields = intersection of all field sets
        common_fields = set.intersection(*field_sets) if len(field_sets) > 0 else set()

        # Total unique fields = union of all field sets
        total_unique_fields = set.union(*field_sets) if len(field_sets) > 0 else set()

        if not total_unique_fields or len(total_unique_fields) == 0:
            return 0.0

        # Calculate stability ratio
        stability = len(common_fields) / len(total_unique_fields)

        return stability

    except Exception as e:
        print(f"Error calculating schema stability: {e}")
        return 0.0


async def extract_structured_data(
    prompt: str, transcript: str, schema_json: str, model: str
) -> dict:
    """Extract structured data from transcript using the experiment's prompt and schema"""
    try:
        schema = json.loads(schema_json)

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": transcript},
            ],
            response_format={"type": "json_object"},
            tool_choice="auto",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "structured_response",
                        "description": "Produce a structured response complying with the fact find JSON schema.",
                        "parameters": schema
                    }
                }
            ],
            temperature=0,
            seed=54321
        )

        # Extract from function call (same as run.py)
        result = response.choices[0]
        if hasattr(result, "message") and hasattr(result.message, "tool_calls"):
            for tool in result.message.tool_calls:
                if tool.function.name == "structured_response":
                    return json.loads(tool.function.arguments)

        # Fallback: try direct JSON in message content
        try:
            return json.loads(result.message.content)
        except Exception:
            raise Exception("Failed to parse structured response")

    except Exception as e:
        raise Exception(f"Extraction failed: {str(e)}")


async def review_extraction(
    transcript: str,
    initial_extraction: dict,
    schema_json: str,
    model: str
) -> dict:
    """
    Review initial extraction and identify missing or hallucinated items.

    Returns structured review data with:
    - missing_items: List of items in transcript but not extracted
    - hallucinated_items: List of items extracted but not in transcript
    - issues: Other extraction quality problems
    - summary: Overall quality assessment
    """
    try:
        review_prompt = f"""You are an expert data extraction reviewer. Compare the extracted JSON data against the original transcript to identify quality issues.

Original Transcript:
{transcript}

Extracted Data:
{json.dumps(initial_extraction, indent=2)}

Expected Schema:
{schema_json}

Identify:
1. MISSING ITEMS: Data present in transcript but not captured in extraction
2. HALLUCINATED ITEMS: Data in extraction not supported by transcript
3. OTHER ISSUES: Incorrect values, wrong structure, misclassifications

Be thorough and precise. Cite specific evidence from the transcript."""

        review_schema = {
            "type": "object",
            "properties": {
                "missing_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "description": "Category like 'assets', 'clients', 'incomes'"},
                            "description": {"type": "string", "description": "What's missing"},
                            "evidence": {"type": "string", "description": "Quote from transcript supporting this"}
                        },
                        "required": ["category", "description", "evidence"]
                    }
                },
                "hallucinated_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "field_path": {"type": "string", "description": "Path like 'clients[0].name'"},
                            "extracted_value": {"description": "The incorrectly extracted value"},
                            "reasoning": {"type": "string", "description": "Why it's not supported"}
                        },
                        "required": ["category", "field_path", "reasoning"]
                    }
                },
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "description": "Type like 'incorrect_value', 'wrong_structure'"},
                            "field_path": {"type": "string"},
                            "description": {"type": "string"}
                        },
                        "required": ["type", "field_path", "description"]
                    }
                },
                "summary": {"type": "string", "description": "Overall quality assessment"}
            },
            "required": ["missing_items", "hallucinated_items", "issues", "summary"],
            "additionalProperties": False
        }

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert data extraction reviewer."},
                {"role": "user", "content": review_prompt},
            ],
            response_format={"type": "json_object"},
            tool_choice="auto",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "review_result",
                        "description": "Return review findings with missing items, hallucinations, and issues",
                        "parameters": review_schema
                    }
                }
            ],
            temperature=0,
            seed=54321
        )

        # Extract from function call
        result = response.choices[0]
        if hasattr(result, "message") and hasattr(result.message, "tool_calls"):
            for tool in result.message.tool_calls:
                if tool.function.name == "review_result":
                    return json.loads(tool.function.arguments)

        # Fallback: try direct JSON in message content
        try:
            return json.loads(result.message.content)
        except Exception:
            raise Exception("Failed to parse review response")

    except Exception as e:
        raise Exception(f"Review failed: {str(e)}")


async def extract_with_review(
    prompt: str,
    transcript: str,
    schema_json: str,
    initial_extraction: dict,
    review_data: dict,
    model: str
) -> dict:
    """
    Second-pass extraction incorporating review feedback.
    Produces refined extraction based on initial attempt and review findings.
    """
    try:
        schema = json.loads(schema_json)

        # Build enhanced prompt with review feedback
        enhanced_prompt = f"""{prompt}

IMPORTANT: This is a SECOND PASS extraction. Review the initial extraction and the identified issues below, then produce a CORRECTED extraction.

Initial Extraction (First Pass):
{json.dumps(initial_extraction, indent=2)}

Review Findings:
{json.dumps(review_data, indent=2)}

Instructions:
1. Fix all MISSING ITEMS by adding the data from the transcript
2. Remove or correct all HALLUCINATED ITEMS that aren't supported by the transcript
3. Fix any OTHER ISSUES identified in the review
4. Keep all correct items from the initial extraction
5. Ensure the output strictly follows the schema

Produce the FINAL, CORRECTED extraction."""

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": enhanced_prompt},
                {"role": "user", "content": transcript},
            ],
            response_format={"type": "json_object"},
            tool_choice="auto",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "structured_response",
                        "description": "Produce a corrected structured response based on review feedback",
                        "parameters": schema
                    }
                }
            ],
            temperature=0,
            seed=54321
        )

        # Extract from function call
        result = response.choices[0]
        if hasattr(result, "message") and hasattr(result.message, "tool_calls"):
            for tool in result.message.tool_calls:
                if tool.function.name == "structured_response":
                    return json.loads(tool.function.arguments)

        # Fallback: try direct JSON in message content
        try:
            return json.loads(result.message.content)
        except Exception:
            raise Exception("Failed to parse refined extraction response")

    except Exception as e:
        raise Exception(f"Second-pass extraction failed: {str(e)}")


async def run_judge(
    transcript: str,
    predicted_facts: dict,
    judge_config: dict,
    model: str,
    gold_facts: dict = None
) -> dict:
    """
    Run a two-stage LLM judge to label facts as TP/FP/FN.

    First call: Derive all expected financial facts (gold_facts) from the transcript.
    Second call: Label facts as TP, FP, FN, and produce match links.

    The LLM does NOT compute metrics.

    Args:
        transcript: Original conversation text
        predicted_facts: Facts extracted by the model being evaluated
        judge_config: UI-driven configuration (entity_types, tolerances, etc.)
        model: LLM model to use for judging
        gold_facts: Optional reference facts (if None, judge derives from transcript)

    Returns:
        JudgeResult dict with gold_facts and predicted_facts arrays, each containing
        labeled facts with TP/FP/FN status and match links
    """
    try:
        # ===== Stage 1: Get (or derive) gold_facts =====
        if gold_facts is None:
            # System Prompt for gold facts
            system_prompt_gold = """
Your job is to read the transcript and extract all expected financial facts (the gold standard). 
Identify EVERY relevant fact from the transcript for the specified entity types.

You must output ONLY a JSON array of fact objects, following the output schema. 
Do not include any matches to predictions, nor compute true/false positives/negatives.
"""
            entity_types_str = ", ".join(judge_config.get("entity_types", [])) or "all types"
            profile = judge_config.get("profile_name", "custom")
            extra_instructions = judge_config.get("extra_instructions", "")
            extra_str = f"\n\nAdditional Instructions:\n{extra_instructions}" if extra_instructions else ""

            user_prompt_gold = f"""Configuration:
- Profile: {profile}
- Entity types in scope: {entity_types_str}
{extra_str}

Transcript:
{transcript}

Task: Extract every relevant fact from the transcript appropriate for the entity types in scope.
For each fact, provide:
- id: Any unique identifier string (e.g., "g1", "g2" ...)
- fact_type: Type of fact (e.g., asset, debt, income, client)
- fields: An object containing all the fact's data (e.g., {{"type": "home", "value": 425000}})
- in_scope: true if type is among the in-scope entity types, false otherwise

Example output format:
[
  {{
    "id": "g1",
    "fact_type": "asset",
    "fields": {{"type": "home", "value": 425000, "address": "123 Main St"}},
    "in_scope": true
  }}
]

Return ONLY the JSON array, no explanations.
"""

            gold_schema = {
                "type": "object",
                "properties": {
                    "facts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string", "description": "Unique identifier (e.g., 'g1', 'g2')"},
                                "fact_type": {"type": "string", "description": "Fact type (asset, debt, income, client, etc.)"},
                                "description": {"type": "string", "description": "Very detailed description of the fact's data with all attributes and values"},
                                "in_scope": {"type": "boolean", "description": "Is fact type in evaluation scope?"}
                            },
                            "required": ["id", "fact_type", "description", "in_scope"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["facts"],
                "additionalProperties": False
            }

            gold_response = await client.chat.completions.create(
                model=model,
                temperature=0.0,
                seed=54321,
                messages=[
                    {"role": "system", "content": system_prompt_gold},
                    {"role": "user", "content": user_prompt_gold},
                ],
                response_format={"type": "json_object"},
                tool_choice="required",
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "strict": True,
                            "name": "gold_facts_list",
                            "description": "List of gold (reference) facts identified from the transcript",
                            "parameters": gold_schema
                        }
                    }
                ]
            )
            result = gold_response.choices[0]
            if hasattr(result, "message") and hasattr(result.message, "tool_calls"):
                for tool in result.message.tool_calls:
                    if tool.function.name == "gold_facts_list":
                        gold_facts = json.loads(tool.function.arguments)["facts"]
                        break
                else:
                    raise Exception("No gold_facts found in tool_calls")
            else:
                try:
                    # In case LLM returns JSON directly
                    gold_facts = json.loads(result.message.content)
                except Exception:
                    raise Exception("Failed to parse gold_facts")
        # If gold_facts is provided and not a list, assume dict contains "gold_facts"
        elif isinstance(gold_facts, dict) and "gold_facts" in gold_facts:
            gold_facts = gold_facts["gold_facts"]

        # ===== Stage 2: Do Judging =====
        # System Prompt for judging
        system_prompt_judge = """
Your job is to:
1. Compare the provided gold (expected) facts with the predicted financial facts from the model.
2. For each fact in both lists, label as:
   - TP (true positive): Predicted fact correctly matches a gold fact
   - FP (false positive): Predicted fact has no match in gold facts (hallucination)
   - FN (false negative): Gold fact has no match in predicted facts (missed)
3. Include matched_ids on both gold and predicted facts
4. Do NOT compute evaluation metrics.

Output ONLY a JSON object matching the specified schema.
"""

        # Re-use matching rules, etc.
        entity_types_str = ", ".join(judge_config.get("entity_types", [])) or "all types"
        profile = judge_config.get("profile_name", "custom")
        matching_rules = []
        if judge_config.get("numeric_tolerance_percent", 0) > 0:
            matching_rules.append(f"- Numeric values within ±{judge_config['numeric_tolerance_percent']}% are considered matching")
        if judge_config.get("date_granularity"):
            matching_rules.append(f"- Dates matched at {judge_config['date_granularity']} granularity")
        if judge_config.get("case_insensitive_strings"):
            matching_rules.append("- String comparisons are case-insensitive")
        if judge_config.get("ignore_minor_wording_diffs"):
            matching_rules.append("- Minor wording differences are ignored (focus on meaning)")
        if judge_config.get("require_all_fields_match"):
            matching_rules.append("- ALL fields must match for a TP (strict mode)")
        if judge_config.get("required_key_fields"):
            fields_str = ", ".join(judge_config["required_key_fields"])
            matching_rules.append(f"- These key fields must match: {fields_str}")
        if not judge_config.get("allow_partial_matches", True):
            matching_rules.append("- Partial matches do NOT count as TP")

        matching_rules_str = "\n".join(matching_rules) if matching_rules else "- Use standard exact matching"

        extra_instructions = judge_config.get("extra_instructions", "")
        extra_str = f"\n\nAdditional Instructions:\n{extra_instructions}" if extra_instructions else ""

        user_prompt_judge = f"""Configuration:
- Profile: {profile}
- Entity types in scope: {entity_types_str}

Matching Rules:
{matching_rules_str}{extra_str}

GOLD (Reference) Facts:
{json.dumps(gold_facts, indent=2)}

Predicted Facts (from model):
{json.dumps(predicted_facts, indent=2)}

Task:
1. Compare each gold fact with predicted facts using these matching rules.
2. Label:
   - gold_facts: status = "TP" if matched, "FN" if not found in predictions
   - predicted_facts: status = "TP" if matched, "FP" if not found in gold
3. Include match links (matched_ids) between related facts.
4. Mark in_scope = true for entity types in scope, false otherwise.

IMPORTANT: Each fact must have a "fields" object containing all the fact's data.

Example output format:
{{
  "gold_facts": [
    {{
      "id": "g1",
      "fact_type": "asset",
      "fields": {{"type": "home", "value": 425000, "address": "123 Main St"}},
      "in_scope": true,
      "matched_ids": ["p1"],
      "status": "TP"
    }}
  ],
  "predicted_facts": [
    {{
      "id": "p1",
      "fact_type": "asset",
      "fields": {{"type": "home", "value": 425000, "address": "123 Main St"}},
      "in_scope": true,
      "matched_ids": ["g1"],
      "status": "TP"
    }}
  ],
  "notes": "Optional evaluation notes"
}}

Return the structured result."""

        # Judge output schema (same as before)
        judge_schema = {
            "type": "object",
            "properties": {
                "gold_facts": {
                    "type": "array",
                    "description": "Expected facts derived from the transcript (gold standard)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Unique identifier for this gold fact (e.g., 'g1', 'g2')"},
                            "fact_type": {"type": "string", "description": "Type of fact (e.g., 'asset', 'debt', 'income', 'client')"},
                            "description": {"type": "string", "description": "Very detailed description of the fact's data with all attributes and values"},
                            "in_scope": {"type": "boolean", "description": "Whether this fact type is in scope for evaluation"},
                            "matched_ids": {"type": "array", "items": {"type": "string"}, "description": "IDs of predicted facts that match this gold fact"},
                            "status": {"type": "string", "enum": ["TP", "FN"], "description": "TP if matched with a predicted fact, FN if missed"}
                        },
                        "required": ["id", "fact_type", "description", "in_scope", "matched_ids", "status"],
                        "additionalProperties": False
                    }
                },
                "predicted_facts": {
                    "type": "array",
                    "description": "Facts extracted by the model being evaluated",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Unique identifier for this predicted fact (e.g., 'p1', 'p2')"},
                            "fact_type": {"type": "string", "description": "Type of fact (e.g., 'asset', 'debt', 'income', 'client')"},
                            "description": {"type": "string", "description": "Very detailed description of the fact's data with all attributes and values"},
                            "in_scope": {"type": "boolean", "description": "Whether this fact type is in scope for evaluation"},
                            "matched_ids": {"type": "array", "items": {"type": "string"}, "description": "IDs of gold facts that match this predicted fact"},
                            "status": {"type": "string", "enum": ["TP", "FP"], "description": "TP if matched with a gold fact, FP if hallucinated"}
                        },
                        "required": ["id", "fact_type", "description", "in_scope", "matched_ids", "status"],
                        "additionalProperties": False
                    }
                },
                "notes": {"type": "string", "description": "Optional evaluation notes or observations"}
            },
            "required": ["gold_facts", "predicted_facts", "notes"],
            "additionalProperties": False
        }

        response = await client.chat.completions.create(
            model=model,
            temperature=0.0,
            seed=54321,
            messages=[
                {"role": "system", "content": system_prompt_judge},
                {"role": "user", "content": user_prompt_judge},
            ],
            response_format={"type": "json_object"},
            tool_choice="required",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "strict": True,
                        "name": "judge_result",
                        "description": "Return judge evaluation with labeled facts",
                        "parameters": judge_schema
                    }
                }
            ]
        )

        result = response.choices[0]
        if hasattr(result, "message") and hasattr(result.message, "tool_calls"):
            for tool in result.message.tool_calls:
                if tool.function.name == "judge_result":
                    return json.loads(tool.function.arguments)
        # Fallback: try direct JSON in message content
        try:
            return json.loads(result.message.content)
        except Exception:
            raise Exception("Failed to parse judge result")

    except Exception as e:
        raise Exception(f"Judge evaluation failed: {str(e)}")


async def get_ai_assistance(
    instruction: str,
    current_content: str,
    field_type: str,
    context: str = "",
) -> str:
    """Use GPT-5 to generate or improve prompts and schemas"""
    try:
        if field_type == "prompt":
            system_prompt = """You are an expert at writing clear, effective prompts for LLM tasks.
When asked to create or improve a prompt, you should:
- Make it clear and specific
- Include relevant context and instructions
- Define the expected output format
- Be concise but comprehensive"""

            user_prompt = f"""Instruction: {instruction}

Current content: {current_content if current_content else "(empty - create from scratch)"}

{f"Context: {context}" if context else ""}

Please generate or improve the prompt according to the instruction. Return ONLY the prompt text, no explanations."""

        else:  # schema
            system_prompt = """You are an expert at creating JSON schemas for OpenAI's structured outputs.
When asked to create or improve a JSON schema, you should:
- Follow the OpenAI structured outputs format
- Use appropriate types and descriptions
- Include required fields
- Set additionalProperties to false
- Make it well-structured and complete"""

            user_prompt = f"""Instruction: {instruction}

Current schema: {current_content if current_content else "(empty - create from scratch)"}

{f"Context: {context}" if context else ""}

Please generate or improve the JSON schema according to the instruction. Return ONLY the valid JSON schema, no explanations.
Don't place it between ```json and ```."""

        response = await client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=1
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        raise Exception(f"AI assistance failed: {str(e)}")
