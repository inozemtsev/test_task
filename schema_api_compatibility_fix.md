# Schema API Compatibility Fix

## Error Encountered

```
Error code: 400 - {'error': {'message': "Invalid schema for function 'structured_response'. 
Please ensure it is a valid JSON Schema.", 'type': 'invalid_request_error', 
'param': 'tools[0].function.parameters', 'code': 'invalid_function_parameters'}}
```

## Root Cause

OpenAI's Structured Outputs API supports only a **subset of JSON Schema features**. Advanced features like:
- `"not"` constraints ❌
- `"if/then/else"` conditionals ❌  
- Complex `oneOf` with type constraints ❌
- `patternProperties` ❌

These were added to enforce stricter validation but are **not supported by the API**.

---

## Fixes Applied

### 1. Removed `"not"` Constraint from Generic Fallback

**Before (INVALID):**
```json
{
  "property": {
    "type": "string",
    "not": {
      "enum": [
        "attitude_to_risk",
        "current_value",
        // ... 18 properties
      ]
    }
  }
}
```

**After (VALID):**
```json
{
  "property": {
    "type": "string",
    "description": "Field name - should be a property not defined above with const"
  }
}
```

**Impact:** Generic fallback is now more permissive, but still guided by description.

---

### 2. Removed Complex `oneOf` Constraint on Value

**Before (POTENTIALLY INVALID):**
```json
{
  "value": {
    "oneOf": [
      { "type": "string" },
      { "type": "number" },
      { "type": "boolean" },
      { "type": "null" }
    ]
  }
}
```

**After (VALID):**
```json
{
  "value": {
    "description": "Simple value only - string, number, or boolean. NO nested objects or arrays."
  }
}
```

**Impact:** Value validation is now description-based rather than schema-enforced.

---

## What Still Works

✅ **18 Specific SnapshotValue Definitions** - These are fully supported:
- Each uses `"const"` for property name
- Each specifies exact `type` 
- Each has enum values where applicable

✅ **oneOf Structure** - The top-level `oneOf` with 19 variants is supported

✅ **allOf for Enums** - Used in 7 places to combine `ScalarFact` with enum constraints

✅ **additionalProperties: false** - Strict object validation is supported

✅ **Required Fields** - All required field constraints work

---

## Validation Results

```
✅ No 'not' constraints found
✅ No 'if' constraints found
✅ No 'then' constraints found
✅ No 'else' constraints found
✅ No 'patternProperties' constraints found
✅ SnapshotValue has 'oneOf' with 19 variants
✅ Schema uses 'allOf' in 7 places (supported for enum constraints)
```

---

## Trade-offs Made

### Lost: Hard Schema Enforcement
- ❌ Cannot prevent generic fallback from using defined property names
- ❌ Cannot enforce simple types on value field via schema

### Kept: Strong Guidance via Descriptions
- ✅ 18 specific property definitions force correct usage
- ✅ Descriptions guide LLM behavior
- ✅ API-level validation still enforces structure

### Result: Pragmatic Balance
The schema now:
1. **Works** with OpenAI's Structured Outputs API ✅
2. **Guides** LLM to use specific definitions via `oneOf` order ✅
3. **Documents** expected behavior via descriptions ✅
4. **Enforces** what's possible within API constraints ✅

---

## Schema Structure Now

```
SnapshotValue (oneOf with 19 variants)
├── [1-18] Specific property definitions with const names
│   ├── attitude_to_risk (enum)
│   ├── current_value (number)
│   ├── gross_annual_salary (number)
│   ├── annual_amount (number)
│   ├── monthly_amount (number)
│   ├── employee_contribution_rate (number)
│   ├── employer_contribution_rate (number)
│   ├── monthly_payment (number)
│   ├── interest_rate (number)
│   ├── objective_summary (string)
│   ├── current_state_of_health (enum)
│   ├── smoker_status (enum)
│   └── ... and 6 more
└── [19] Generic fallback (permissive but discouraged via description)
```

---

## How LLM Will Choose

The `oneOf` structure means the LLM will:

1. **Try specific definitions first** (variants 1-18)
2. **Match by property name** using `const` constraints
3. **Fall back to generic** only if no match

**Example:**
```
LLM sees: "attitude_to_risk" in transcript
├─→ Checks variant 1: property = "attitude_to_risk" ✅ MATCH
└─→ Uses that definition with enum constraint
```

```
LLM sees: "some_custom_field" in transcript  
├─→ Checks variants 1-18: no match
└─→ Falls back to variant 19 (generic)
```

---

## Testing Required

### 1. Verify Schema Loads
```bash
python3 -c "import json; json.load(open('start/schema2.json')); print('✅ Valid JSON')"
```

### 2. Test API Call
Run your extraction with the fixed schema:
```bash
python3 run.py --schema start/schema2.json
```

**Expected:** No more 400 errors ✅

### 3. Check Output Quality
Verify that outputs still:
- ✅ Use specific property names (attitude_to_risk, not risk_profile)
- ✅ Use enum values where defined
- ✅ Have `property` field in timeline values
- ✅ Use simple values (not nested objects)

---

## OpenAI Structured Outputs - Supported Features

### ✅ Fully Supported
- `type`, `properties`, `items`
- `required`, `enum`
- `const` (for fixed values)
- `additionalProperties: false`
- `$ref` and `definitions`
- `oneOf` (for union types)
- `allOf` (for combining schemas)

### ⚠️ Limited Support
- `anyOf` (use `oneOf` instead)
- Complex nested `oneOf`

### ❌ Not Supported
- `not` (negation)
- `if/then/else` (conditionals)
- `patternProperties`
- `propertyNames`
- `contains`, `minContains`, `maxContains`

**Reference:** [OpenAI Structured Outputs Documentation](https://platform.openai.com/docs/guides/structured-outputs)

---

## Summary

✅ **Schema is now API-compatible**
✅ **18 specific property definitions remain enforced**
✅ **Generic fallback is more permissive but still guided**
✅ **Should eliminate 400 errors**

The schema still achieves its goal of **standardizing field names** and **improving consistency**, just with **softer enforcement** on the generic fallback to comply with API constraints.

