import openai
import argparse
import json
import sys
import os

def call_gpt5_with_structure(prompt, schema, api_key):
    """
    Calls OpenAI GPT-5 with a prompt, requesting structured JSON output 
    according to the provided schema.

    Args:
        prompt (str): The user prompt to send to GPT-5.
        schema (dict): A JSON schema dict describing the desired output structure.
        api_key (str): OpenAI API key.

    Returns:
        dict: The structured response from GPT-5 as Python dict.
    """
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-5.1",
        messages=[
            {"role": "system", "content": '''
                Your are an assistant which returns structured JSON data from a fact find call transcript. 
                Try to summarize in "value" fields as much as possible. 
            '''},
            {"role": "user", "content": prompt}
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
    # Look for the function call/structured JSON in the first choice
    result = response.choices[0]
    if hasattr(result, "message") and hasattr(result.message, "tool_calls"):
        for tool in result.message.tool_calls:
            if tool.function.name == "structured_response":
                import json
                return json.loads(tool.function.arguments)
    # fallback: try direct JSON in message content
    try:
        import json
        return json.loads(result.message.content)
    except Exception:
        raise RuntimeError("Failed to parse structured GPT-5 response.")

def main():
    parser = argparse.ArgumentParser(description="Process a transcript with GPT-5 to structured JSON via schema.")
    parser.add_argument("--transcript_file", default="synthetic_transcript1.txt", help="Path to the transcript text file.")
    parser.add_argument("--schema_file", default="schema.json", help="Path to the schema JSON file.")
    parser.add_argument("--output_file", default="structured_result_1.json", help="Path to save the output structured JSON file.")
    # No CLI argument for API key; use environment variable OPENAI_API_KEY instead.
    args = parser.parse_args()

    # Read transcript
    try:
        with open(args.transcript_file, 'r', encoding='utf-8') as tf:
            transcript = tf.read()
    except Exception as e:
        print(f"Error reading transcript file: {e}", file=sys.stderr)
        sys.exit(1)

    # Read schema
    try:
        with open(args.schema_file, 'r', encoding='utf-8') as sf:
            schema = json.load(sf)
    except Exception as e:
        print(f"Error reading schema file: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        print(os.environ.get("OPENAI_API_KEY"))
        result = call_gpt5_with_structure(transcript, schema, os.environ.get("OPENAI_API_KEY"))
        with open(args.output_file, "w", encoding="utf-8") as outfile:
            outfile.write(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error during GPT-5 call or response handling: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
