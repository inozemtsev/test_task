"""
Schema utilities for JSON Schema field extraction and comparison.

This module provides functions to:
- Extract leaf field paths from JSON Schema definitions
- Flatten nested dictionaries into field paths
- Calculate field overlap between extracted data and schemas
"""
import json


def flatten_dict_keys(d: dict | list, parent_key: str = '', sep: str = '.') -> set:
    """
    Recursively flatten a nested dictionary (and lists) and return all key paths.

    Lists are marked by [] in the path, so all list items at the same level share the same path.

    Example:
        {"a": {"b": 1, "c": {"d": 2}, "e": [ {"x":5}, {"x":6} ]}}
        -> {"a.b", "a.c.d", "a.e[].x"}

    Args:
        d: Dictionary or list to flatten
        parent_key: Current parent key path (used in recursion)
        sep: Separator for key path components

    Returns:
        Set of all leaf field paths
    """
    keys = set()
    if isinstance(d, dict):
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict) and v:
                keys.update(flatten_dict_keys(v, new_key, sep=sep))
            elif isinstance(v, list):
                list_key = f"{new_key}[]"
                # Always add the list path
                if not v:
                    # Empty list: only mark the list itself
                    keys.add(list_key)
                else:
                    for item in v:
                        # For each item, pass the list_key as parent
                        keys.update(flatten_dict_keys(item, list_key, sep=sep))
            else:
                # Only add the path if it's a leaf (not a non-empty dict or list)
                keys.add(new_key)
    elif isinstance(d, list):
        # Top-level list, rare: treat each item as root
        for item in d:
            keys.update(flatten_dict_keys(item, parent_key + '[]' if parent_key else '[]', sep=sep))
    else:
        # Base case: leaf value, just parent_key
        if parent_key:
            keys.add(parent_key)
    return keys


def get_schema_fields(schema_json: str) -> set[str]:
    """
    Extract all LEAF field paths from a JSON schema.
    Handles $ref, allOf, anyOf, nested properties, and arrays.
    Only returns terminal/leaf fields (fields that hold actual values, not containers).

    Args:
        schema_json: JSON string of the schema

    Returns:
        Set of leaf field paths (e.g., {'clients[].client_id', 'assets[].static.asset_type.value'})
    """
    try:
        schema = json.loads(schema_json)

        def resolve_ref(ref_path: str, root_schema: dict) -> dict:
            """Resolve a $ref path like '#/definitions/Client'"""
            if not ref_path.startswith("#/"):
                return {}

            parts = ref_path[2:].split("/")  # Remove '#/' and split
            current = root_schema

            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return {}

            return current if isinstance(current, dict) else {}

        def merge_schemas(schemas: list[dict]) -> dict:
            """Merge multiple schemas (for allOf, anyOf, etc.)"""
            merged = {}
            for s in schemas:
                if isinstance(s, dict):
                    # Merge properties
                    if "properties" in s:
                        if "properties" not in merged:
                            merged["properties"] = {}
                        merged["properties"].update(s["properties"])
                    # Copy over type if not set
                    if "type" in s and "type" not in merged:
                        merged["type"] = s["type"]
            return merged

        def extract_fields(obj: dict, parent_key: str = '', sep: str = '.', visited: set = None) -> set[str]:
            """Recursively extract LEAF field paths from schema object"""
            if visited is None:
                visited = set()

            fields = set()

            if not isinstance(obj, dict):
                return fields

            # Prevent infinite recursion from circular refs
            obj_id = id(obj)
            if obj_id in visited:
                return fields
            visited.add(obj_id)

            # Handle $ref
            if "$ref" in obj:
                ref_schema = resolve_ref(obj["$ref"], schema)
                fields.update(extract_fields(ref_schema, parent_key, sep, visited.copy()))
                return fields

            # Handle allOf (merge all schemas into one and process)
            if "allOf" in obj:
                # Resolve all $refs and merge all schemas
                resolved_items = []
                for item in obj["allOf"]:
                    if isinstance(item, dict):
                        if "$ref" in item:
                            ref_schema = resolve_ref(item["$ref"], schema)
                            resolved_items.append(ref_schema)
                        else:
                            resolved_items.append(item)

                # Merge all resolved items
                merged = merge_schemas(resolved_items)

                # Process the merged schema once
                fields.update(extract_fields(merged, parent_key, sep, visited.copy()))
                return fields

            # Handle anyOf (treat as union of all possibilities)
            if "anyOf" in obj:
                # Check if anyOf contains complex types or just simple types
                has_complex = False
                for item in obj["anyOf"]:
                    if isinstance(item, dict) and item.get("type") != "null":
                        if "properties" in item or "allOf" in item or "$ref" in item:
                            has_complex = True
                            break

                if has_complex:
                    # Process each complex alternative
                    for item in obj["anyOf"]:
                        if isinstance(item, dict) and item.get("type") != "null":
                            fields.update(extract_fields(item, parent_key, sep, visited.copy()))
                else:
                    # All alternatives are simple types, treat as leaf
                    if parent_key:
                        fields.add(parent_key)

                return fields

            # Handle properties
            if "properties" in obj:
                for prop_name, prop_schema in obj["properties"].items():
                    new_key = f"{parent_key}{sep}{prop_name}" if parent_key else prop_name

                    if not isinstance(prop_schema, dict):
                        fields.add(new_key)
                        continue

                    # Resolve $ref first
                    if "$ref" in prop_schema:
                        ref_schema = resolve_ref(prop_schema["$ref"], schema)
                        prop_schema = {**ref_schema, **{k: v for k, v in prop_schema.items() if k != "$ref"}}

                    # Check if this is a leaf or has children
                    prop_type = prop_schema.get("type")
                    has_properties = "properties" in prop_schema or "allOf" in prop_schema or "anyOf" in prop_schema

                    # Array handling
                    if prop_type == "array" and "items" in prop_schema:
                        array_key = f"{new_key}[]"
                        items = prop_schema["items"]

                        if isinstance(items, dict):
                            # Resolve $ref in items
                            if "$ref" in items:
                                items = resolve_ref(items["$ref"], schema)

                            # Check if items are objects with properties
                            if items.get("type") == "object" or "properties" in items or "allOf" in items:
                                fields.update(extract_fields(items, array_key, sep, visited.copy()))
                            else:
                                # Array of primitives
                                fields.add(array_key)
                    # Object with nested properties
                    elif (prop_type == "object" and has_properties) or has_properties:
                        fields.update(extract_fields(prop_schema, new_key, sep, visited.copy()))
                    # Leaf field (primitive or object without properties)
                    else:
                        fields.add(new_key)

            return fields

        return extract_fields(schema)

    except Exception as e:
        print(f"Error extracting schema fields: {e}")
        import traceback
        traceback.print_exc()
        return set()


def calculate_field_overlap(extracted_data: dict, schema_json: str) -> dict:
    """
    Calculate comprehensive field overlap analysis between extracted data and schema.

    Args:
        extracted_data: The extracted data dictionary
        schema_json: JSON string of the expected schema

    Returns:
        dict with:
        - jaccard: Jaccard similarity coefficient (intersection / union)
        - missing_fields: Fields in schema but not in extraction (list)
        - extra_fields: Fields in extraction but not in schema (list)
        - intersection_count: Number of matching fields
        - union_count: Total unique fields
    """
    try:
        # Get field sets
        extracted_fields = flatten_dict_keys(extracted_data)
        schema_fields = get_schema_fields(schema_json)

        if not schema_fields:
            # No schema fields to compare against
            return {
                "jaccard": 0.0,
                "missing_fields": [],
                "extra_fields": sorted(list(extracted_fields)),
                "intersection_count": 0,
                "union_count": len(extracted_fields)
            }

        # Calculate set operations
        intersection = extracted_fields & schema_fields
        union = extracted_fields | schema_fields
        missing = schema_fields - extracted_fields  # In schema, not extracted
        extra = extracted_fields - schema_fields     # Extracted, not in schema

        # Calculate Jaccard similarity
        jaccard = len(intersection) / len(union) if union else 0.0

        return {
            "jaccard": jaccard,
            "missing_fields": sorted(list(missing)),
            "extra_fields": sorted(list(extra)),
            "intersection_count": len(intersection),
            "union_count": len(union),
        }

    except Exception as e:
        print(f"Error calculating field overlap: {e}")
        import traceback
        traceback.print_exc()
        return {
            "jaccard": 0.0,
            "missing_fields": [],
            "extra_fields": [],
            "intersection_count": 0,
            "union_count": 0,
        }
