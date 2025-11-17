import json
from openai import AsyncOpenAI
from config import settings

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


def flatten_dict_keys(d: dict, parent_key: str = '', sep: str = '.') -> set:
    """
    Recursively flatten a nested dictionary and return all key paths.

    Example:
        {"a": {"b": 1, "c": {"d": 2}}} -> {"a.b", "a.c.d"}
    """
    keys = set()
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        keys.add(new_key)
        if isinstance(v, dict):
            keys.update(flatten_dict_keys(v, new_key, sep=sep))
    return keys


def get_schema_fields(schema: dict, parent_key: str = '', sep: str = '.') -> set:
    """
    Extract all field paths from a JSON schema.
    Handles nested properties, arrays, etc.
    """
    fields = set()

    if "properties" in schema:
        for prop_name, prop_schema in schema["properties"].items():
            new_key = f"{parent_key}{sep}{prop_name}" if parent_key else prop_name
            fields.add(new_key)

            # Recursively handle nested objects
            if isinstance(prop_schema, dict):
                if prop_schema.get("type") == "object" and "properties" in prop_schema:
                    fields.update(get_schema_fields(prop_schema, new_key, sep=sep))
                elif prop_schema.get("type") == "array" and "items" in prop_schema:
                    items = prop_schema["items"]
                    if isinstance(items, dict) and items.get("type") == "object":
                        fields.update(get_schema_fields(items, new_key, sep=sep))

    return fields


def calculate_schema_overlap(extracted_data: dict, schema_json: str) -> float:
    """
    Calculate schema stability - the percentage of schema fields present in extracted data.

    Returns:
        float: Percentage between 0.0 and 1.0
    """
    try:
        schema = json.loads(schema_json)

        # Get all fields defined in schema
        schema_fields = get_schema_fields(schema)

        if not schema_fields:
            # If schema has no fields, return 1.0 (100%)
            return 1.0

        # Get all fields present in extracted data
        extracted_fields = flatten_dict_keys(extracted_data)

        # Calculate overlap
        present_fields = schema_fields.intersection(extracted_fields)
        overlap_percentage = len(present_fields) / len(schema_fields)

        return overlap_percentage

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
            ]
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


async def evaluate_characteristic(
    characteristic_prompt: str,
    transcript: str,
    extracted_data: dict,
    model: str,
    schema_json: str = None,
) -> tuple[bool, str, dict[str, float], dict]:
    """Evaluate a single characteristic using the judge's model"""
    try:
        evaluation_prompt = f"""{characteristic_prompt}

Original Transcript:
{transcript}

Extracted Data:
{json.dumps(extracted_data, indent=2)}

Based on the above, evaluate whether this test case passes."""

        # Use function calling with schema if provided, otherwise use default schema
        use_custom_schema = False
        if schema_json and schema_json.strip():
            try:
                schema = json.loads(schema_json)

                # Validate it's a valid schema object
                if isinstance(schema, dict) and "type" in schema:
                    use_custom_schema = True
            except (json.JSONDecodeError, ValueError):
                pass

        if use_custom_schema:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": """
                     Compare the extracted JSON data with the raw transript and evaluate if the test case passes.
                    """},
                    {"role": "user", "content": evaluation_prompt},
                ],
                response_format={"type": "json_object"},
                tool_choice="auto",
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "evaluation_result",
                            "description": "Return evaluation result with pass/fail, reasoning and metrics",
                            "parameters": schema
                        }
                    }
                ],
            )

            # Extract from function call (same as run.py)
            result = response.choices[0]
            print(result.message.tool_calls)
            if hasattr(result, "message") and hasattr(result.message, "tool_calls"):
                for tool in result.message.tool_calls:
                    if tool.function.name == "evaluation_result":
                        parsed = json.loads(tool.function.arguments)
                        print('METRICS',parsed.get("metrics", {}))
                        return (
                            parsed.get("passes", False),
                            parsed.get("reasoning", ""),
                            parsed.get("metrics", {}),
                            parsed  # Full response
                        )

            # Fallback: try direct JSON in message content
            try:
                parsed = json.loads(result.message.content)
                print('METRICS',parsed.get("metrics", {}))
                return (
                    parsed.get("passes", False),
                    parsed.get("reasoning", ""),
                    parsed.get("metrics", {}),
                    parsed  # Full response
                )
            except Exception:
                raise Exception("Failed to parse evaluation response")
        else:
            # Default to simple JSON object format (no schema provided)
            default_schema = {
                "type": "object",
                "properties": {
                    "passes": {"type": "boolean"},
                    "reasoning": {"type": "string"},
                    "numerator": {
                        "type": "number",
                        "description": "Number of items that passed or were found"
                    },
                    "denominator": {
                        "type": "number",
                        "description": "Total number of items evaluated"
                    },
                    "metrics": {
                        "type": "object",
                        "additionalProperties": {"type": "number"},
                        "description": "Optional detailed metrics (0.0-1.0)"
                    }
                },
                "required": ["passes", "reasoning"],
                "additionalProperties": False
            }

            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert evaluator."},
                    {"role": "user", "content": evaluation_prompt},
                ],
                response_format={"type": "json_object"},
                tool_choice="auto",
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "evaluation_result",
                            "description": "Return evaluation result with pass/fail and reasoning",
                            "parameters": default_schema
                        }
                    }
                ]
            )

            # Extract from function call (same as run.py)
            result = response.choices[0]
            if hasattr(result, "message") and hasattr(result.message, "tool_calls"):
                for tool in result.message.tool_calls:
                    if tool.function.name == "evaluation_result":
                        parsed = json.loads(tool.function.arguments)
                        return (
                            parsed.get("passes", False),
                            parsed.get("reasoning", ""),
                            parsed.get("metrics", {}),
                            parsed  # Full response
                        )

            # Fallback: try direct JSON in message content
            try:
                parsed = json.loads(result.message.content)
                print('METRICS',parsed.get("metrics", {}))
                return (
                    parsed.get("passes", False),
                    parsed.get("reasoning", ""),
                    parsed.get("metrics", {}),
                    parsed  # Full response
                )
            except Exception:
                raise Exception("Failed to parse evaluation response")

    except Exception as e:
        raise Exception(f"Evaluation failed: {str(e)}")


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
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        raise Exception(f"AI assistance failed: {str(e)}")
