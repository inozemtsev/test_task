import asyncio
import copy
import json

from services.llm_service import client
from schemas import JudgeResult

ENTITY_TYPE_ALIASES = {
    "asset": "asset",
    "assets": "asset",
    "property": "property",
    "properties": "property",
    "client": "client",
    "clients": "client",
    "debt": "debt",
    "debts": "debt",
    "liability": "debt",
    "liabilities": "debt",
    "liability_except_mortgage": "debt",
    "income": "income",
    "incomes": "income",
    "expense": "expense",
    "expenses": "expense",
    "pension": "pension",
    "pensions": "pension",
    "account": "account",
    "accounts": "account",
    "saving_investment": "asset",
    "savings": "asset",
    "investment_account": "account",
    "protection_policy": "asset",
    "position": "position",
    "positions": "position",
}


def _normalize_entity_type(entity_type: str | None) -> str:
    if not entity_type:
        return "unknown"
    normalized = entity_type.strip().lower()
    return ENTITY_TYPE_ALIASES.get(normalized, normalized)


JUDGE_PARALLELISM = 4


def _extract_fact_array(source: dict | list | None, fallback_key: str) -> list:
    if source is None:
        return []
    if isinstance(source, list):
        return source
    if isinstance(source, dict):
        if "facts" in source and isinstance(source["facts"], list):
            return source["facts"]
        if fallback_key in source and isinstance(source[fallback_key], list):
            return source[fallback_key]
    raise Exception("Facts must be provided as a list of fact objects.")


def _expand_predicted_facts(predicted_raw) -> list:
    if isinstance(predicted_raw, list):
        return predicted_raw
    if not isinstance(predicted_raw, dict):
        raise Exception("Predicted facts must be a list or dict of fact collections.")

    facts: list[dict] = []
    for key, items in predicted_raw.items():
        if not isinstance(items, list):
            continue
        for idx, raw_item in enumerate(items, start=1):
            if not isinstance(raw_item, dict):
                continue
            fact = copy.deepcopy(raw_item)
            fact_id = (
                fact.get("id")
                or fact.get("position_id")
                or fact.get("asset_id")
                or fact.get("account_id")
                or fact.get("client_id")
                or f"{key}_{idx}"
            )
            fact["id"] = str(fact_id)

            derived_type = (
                fact.get("fact_type")
                or fact.get("position_type")
                or key
            )
            fact["fact_type"] = _normalize_entity_type(derived_type)

            if not fact.get("description"):
                static_block = fact.get("static")
                if isinstance(static_block, dict):
                    static_desc = static_block.get("description")
                    if isinstance(static_desc, dict) and static_desc.get("value"):
                        fact["description"] = static_desc["value"]
                if not fact.get("description"):
                    fact["description"] = json.dumps(
                        {k: v for k, v in fact.items() if k != "description"},
                        ensure_ascii=False,
                    )
            facts.append(fact)

    if not facts:
        raise Exception("Predicted facts must contain at least one fact collection.")
    return facts


def _normalize_facts(
    raw_facts: list,
    prefix: str,
    allowed_entity_types: set[str],
):
    """Ensure each fact has ids, descriptions, and scope flags."""
    normalized = []
    scoped = []
    order_map = {}
    seen_ids = set()

    for idx, raw in enumerate(raw_facts or [], start=1):
        if not isinstance(raw, dict):
            continue
        fact = copy.deepcopy(raw)
        fact_id = str(fact.get("id") or f"{prefix}{idx}")
        if fact_id in seen_ids:
            suffix = 1
            while f"{fact_id}_{suffix}" in seen_ids:
                suffix += 1
            fact_id = f"{fact_id}_{suffix}"
        seen_ids.add(fact_id)
        fact["id"] = fact_id

        fact_type_value = (
            fact.get("fact_type")
            or fact.get("entity_type")
            or fact.get("type")
            or "unknown"
        )
        fact_type = _normalize_entity_type(str(fact_type_value))
        fact["fact_type"] = fact_type

        description = fact.get("description")
        if not description:
            if "fields" in fact:
                description = json.dumps(fact["fields"], ensure_ascii=False)
            else:
                fallback = {k: v for k, v in fact.items() if k != "description"}
                description = json.dumps(fallback, ensure_ascii=False)
        fact["description"] = description

        in_scope = True
        if allowed_entity_types:
            in_scope = fact_type in allowed_entity_types
        fact["in_scope"] = in_scope

        fact["matched_ids"] = []
        fact["status"] = "UNJUDGED"

        normalized.append(fact)
        order_map[fact_id] = len(order_map)
        if in_scope:
            scoped.append(fact)

    return normalized, scoped, order_map


def _fact_prompt_view(fact: dict) -> dict:
    view = {
        "id": fact["id"],
        "fact_type": fact["fact_type"],
        "description": fact.get("description", ""),
    }
    if "fields" in fact:
        view["fields"] = fact["fields"]
    return view


def _append_note(description: str, note: str) -> str:
    if not note:
        return description
    base = description or ""
    return (base + f"\n\nDedup note: {note}").strip()


async def run_judge(
    transcript: str,
    predicted_facts: dict,
    judge_config: dict,
    model: str,
    gold_facts=None,
) -> dict:
    """Dual-pass judge that labels gold and predicted facts with TP/FP/FN tags."""
    del transcript  # Not used in current prompts

    try:
        if gold_facts is None:
            raise Exception(
                "Ground truth facts not provided. Generate and store ground truth for this judge first."
            )
        judge_config = judge_config or {}

        gold_facts_list = _extract_fact_array(gold_facts, "gold_facts")
        predicted_facts_list = _expand_predicted_facts(predicted_facts)

        allowed_entity_types = {
            _normalize_entity_type(fact_type)
            for fact_type in judge_config.get("entity_types", [])
            if fact_type
        }

        gold_facts_normalized, scoped_gold_facts, gold_order = _normalize_facts(
            gold_facts_list, "g", allowed_entity_types
        )
        predicted_facts_normalized, scoped_predicted_facts, predicted_order = _normalize_facts(
            predicted_facts_list, "p", allowed_entity_types
        )

        gold_map = {fact["id"]: fact for fact in gold_facts_normalized}
        predicted_map = {fact["id"]: fact for fact in predicted_facts_normalized}

        entity_types_str = ", ".join(judge_config.get("entity_types", [])) or "all types"
        profile = judge_config.get("profile_name", "custom")
        matching_rules = []
        if judge_config.get("numeric_tolerance_percent", 0) > 0:
            matching_rules.append(
                f"- Numeric values within ±{judge_config['numeric_tolerance_percent']}% are considered matching"
            )
        if judge_config.get("date_granularity"):
            matching_rules.append(
                f"- Dates matched at {judge_config['date_granularity']} granularity"
            )
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

        base_config_section = f"""Configuration:
- Profile: {profile}
- Entity types in scope: {entity_types_str}

Matching Rules:
{matching_rules_str}{extra_str}
"""

        predicted_prompt_json = json.dumps(
            [_fact_prompt_view(f) for f in scoped_predicted_facts],
            ensure_ascii=False,
            indent=2,
        )
        gold_prompt_json = json.dumps(
            [_fact_prompt_view(f) for f in scoped_gold_facts], ensure_ascii=False, indent=2
        )

        gold_fact_schema = {
            "type": "object",
            "properties": {
                "gold_fact_id": {"type": "string"},
                "status": {"type": "string", "enum": ["TP", "FN"]},
                "matched_predicted_id": {"type": ["string", "null"]},
                "reasoning": {"type": "string"},
            },
            "required": ["gold_fact_id", "status", "matched_predicted_id", "reasoning"],
            "additionalProperties": False,
        }
        predicted_fact_schema = {
            "type": "object",
            "properties": {
                "predicted_fact_id": {"type": "string"},
                "status": {"type": "string", "enum": ["TP", "FP"]},
                "matched_gold_id": {"type": ["string", "null"]},
                "reasoning": {"type": "string"},
            },
            "required": ["predicted_fact_id", "status", "matched_gold_id", "reasoning"],
            "additionalProperties": False,
        }

        gold_system_prompt = (
            "You are evaluating whether a single gold (reference) fact is covered by the model's predicted facts. "
            "Consider the supplied matching rules carefully. Return ONLY the JSON object described by the schema."
        )
        predicted_system_prompt = (
            "You are evaluating whether a single predicted fact matches any of the gold (reference) facts. "
            "Consider the supplied matching rules carefully. Return ONLY the JSON object described by the schema."
        )

        gold_decisions = {}
        predicted_decisions = {}
        reasoning_notes = []
        semaphore = asyncio.Semaphore(JUDGE_PARALLELISM)

        async def _call_fact_tool(tool_name, tool_description, schema, system_prompt, user_prompt):
            response = await client.chat.completions.create(
                model=model,
                temperature=0.0,
                seed=54321,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                tool_choice="required",
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "strict": True,
                            "name": tool_name,
                            "description": tool_description,
                            "parameters": schema,
                        },
                    }
                ],
            )

            choice = response.choices[0]
            if hasattr(choice, "message") and hasattr(choice.message, "tool_calls"):
                for tool in choice.message.tool_calls:
                    if tool.function.name == tool_name:
                        return json.loads(tool.function.arguments)
            return json.loads(choice.message.content)

        async def _judge_single_gold(fact: dict):
            user_prompt = (
                f"{base_config_section}\n\n"
                f"Gold fact to evaluate:\n{json.dumps(_fact_prompt_view(fact), ensure_ascii=False, indent=2)}\n\n"
                f"Predicted facts to compare:\n{predicted_prompt_json}\n\n"
                "Return the JSON verdict."
            )
            async with semaphore:
                decision = await _call_fact_tool(
                    "gold_fact_verdict",
                    "Return TP/FN decision for a single gold fact",
                    gold_fact_schema,
                    gold_system_prompt,
                    user_prompt,
                )
            return fact["id"], decision

        async def _judge_single_predicted(fact: dict):
            user_prompt = (
                f"{base_config_section}\n\n"
                f"Predicted fact to evaluate:\n{json.dumps(_fact_prompt_view(fact), ensure_ascii=False, indent=2)}\n\n"
                f"Gold facts to compare:\n{gold_prompt_json}\n\n"
                "Return the JSON verdict."
            )
            async with semaphore:
                decision = await _call_fact_tool(
                    "predicted_fact_verdict",
                    "Return TP/FP decision for a single predicted fact",
                    predicted_fact_schema,
                    predicted_system_prompt,
                    user_prompt,
                )
            return fact["id"], decision

        if scoped_gold_facts:
            gold_results = await asyncio.gather(*[_judge_single_gold(f) for f in scoped_gold_facts])
            for fact_id, decision in gold_results:
                gold_decisions[fact_id] = decision
                if decision.get("reasoning"):
                    reasoning_notes.append(f"Gold {fact_id}: {decision['reasoning']}")

        if scoped_predicted_facts:
            predicted_results = await asyncio.gather(
                *[_judge_single_predicted(f) for f in scoped_predicted_facts]
            )
            for fact_id, decision in predicted_results:
                predicted_decisions[fact_id] = decision
                if decision.get("reasoning"):
                    reasoning_notes.append(f"Predicted {fact_id}: {decision['reasoning']}")

        match_links = set()
        gold_initial_status = {}
        gold_declared_match = {}
        predicted_initial_status = {}
        predicted_declared_match = {}

        for fact in scoped_gold_facts:
            decision = gold_decisions.get(fact["id"], {})
            status = decision.get("status", "FN")
            gold_initial_status[fact["id"]] = status
            matched_pred = decision.get("matched_predicted_id")
            gold_declared_match[fact["id"]] = matched_pred
            if (
                status == "TP"
                and matched_pred
                and matched_pred in predicted_map
                and predicted_map[matched_pred]["in_scope"]
            ):
                match_links.add((fact["id"], matched_pred))

        for fact in scoped_predicted_facts:
            decision = predicted_decisions.get(fact["id"], {})
            status = decision.get("status", "FP")
            predicted_initial_status[fact["id"]] = status
            matched_gold = decision.get("matched_gold_id")
            predicted_declared_match[fact["id"]] = matched_gold
            if (
                status == "TP"
                and matched_gold
                and matched_gold in gold_map
                and gold_map[matched_gold]["in_scope"]
            ):
                match_links.add((matched_gold, fact["id"]))

        dedup_notes = []
        gold_fact_notes = {fact["id"]: [] for fact in gold_facts_normalized}
        predicted_fact_notes = {fact["id"]: [] for fact in predicted_facts_normalized}

        for pid, status in predicted_initial_status.items():
            if status != "TP":
                continue
            gid = predicted_declared_match.get(pid)
            if not gid:
                continue
            if gid in gold_initial_status and gold_initial_status[gid] == "FN":
                match_links.add((gid, pid))
                gold_initial_status[gid] = "TP"
                note = f"Gold fact {gid} forced to TP because predicted fact {pid} matched it."
                dedup_notes.append(note)
                gold_fact_notes[gid].append(note)

        for gid, matched_pid in gold_declared_match.items():
            if not matched_pid:
                continue
            if gold_initial_status.get(gid) != "TP":
                continue
            if predicted_initial_status.get(matched_pid) == "FP":
                if (gid, matched_pid) in match_links:
                    match_links.remove((gid, matched_pid))
                gold_initial_status[gid] = "FN"
                note = (
                    f"Gold fact {gid} downgraded because predicted fact {matched_pid} labeled itself FP."
                )
                dedup_notes.append(note)
                gold_fact_notes[gid].append(note)

        gold_to_pred = {}
        for gid, pid in list(match_links):
            gold_to_pred.setdefault(gid, []).append(pid)

        for gid, pid_list in gold_to_pred.items():
            if len(pid_list) <= 1:
                continue
            sorted_pids = sorted(pid_list, key=lambda pid: predicted_order.get(pid, 0))
            for pid in sorted_pids[1:]:
                if (gid, pid) in match_links:
                    match_links.remove((gid, pid))
                predicted_initial_status[pid] = "FP"
                note = f"Predicted fact {pid} marked FP because gold {gid} already matched another prediction."
                dedup_notes.append(note)
                predicted_fact_notes[pid].append(note)

        gold_match_lookup = {}
        predicted_match_lookup = {}
        for gid, pid in match_links:
            gold_match_lookup.setdefault(gid, []).append(pid)
            predicted_match_lookup.setdefault(pid, []).append(gid)

        for matches in gold_match_lookup.values():
            matches.sort(key=lambda pid: predicted_order.get(pid, float("inf")))
        for matches in predicted_match_lookup.values():
            matches.sort(key=lambda gid: gold_order.get(gid, float("inf")))

        final_gold = []
        for fact in gold_facts_normalized:
            fact_copy = copy.deepcopy(fact)
            if not fact_copy["in_scope"]:
                fact_copy["status"] = "FN"
                fact_copy["matched_ids"] = []
            else:
                matches = gold_match_lookup.get(fact_copy["id"], [])
                fact_copy["matched_ids"] = matches
                fact_copy["status"] = "TP" if matches else "FN"
            if gold_fact_notes[fact_copy["id"]]:
                fact_copy["description"] = _append_note(
                    fact_copy["description"], " ".join(gold_fact_notes[fact_copy["id"]])
                )
            final_gold.append(fact_copy)

        final_predicted = []
        for fact in predicted_facts_normalized:
            fact_copy = copy.deepcopy(fact)
            if not fact_copy["in_scope"]:
                fact_copy["status"] = "FP"
                fact_copy["matched_ids"] = []
            else:
                matches = predicted_match_lookup.get(fact_copy["id"], [])
                fact_copy["matched_ids"] = matches
                fact_copy["status"] = "TP" if matches else "FP"
            if predicted_fact_notes[fact_copy["id"]]:
                fact_copy["description"] = _append_note(
                    fact_copy["description"], " ".join(predicted_fact_notes[fact_copy["id"]])
                )
            final_predicted.append(fact_copy)

        notes_sections = []
        if dedup_notes:
            notes_sections.append(
                "Dedup adjustments:\n" + "\n".join(f"- {note}" for note in dedup_notes)
            )
        if reasoning_notes:
            trimmed = reasoning_notes[:10]
            notes_sections.append(
                "LLM reasoning samples:\n" + "\n".join(f"- {reason}" for reason in trimmed)
            )
        notes_text = "\n\n".join(notes_sections) if notes_sections else "Dual-pass judge completed."

        result_payload = {
            "gold_facts": final_gold,
            "predicted_facts": final_predicted,
            "notes": notes_text,
        }

        JudgeResult(**result_payload)
        return result_payload

    except Exception as e:
        raise Exception(f"Judge evaluation failed: {str(e)}")
