# Schema Fixes Applied to schema2.json

## Problems Identified in res1.json and res2.json

### 🔴 Critical Issues Found:

1. **Missing `property` field in timeline values** - ALL timeline entries lack required `property` field
2. **Using `label` instead of `property`** - res2.json uses non-existent `label` field
3. **Nested objects in values** - res2.json uses `{"amount": 165000, "currency": "USD"}` instead of simple `165000`
4. **Free-form strings instead of enums** - Not using standardized enum values
5. **Generic fallback too permissive** - Allowed LLM to ignore specific SnapshotValue definitions
6. **Inconsistent null handling** - Mixing null with descriptive text

---

## ✅ Fixes Applied to Schema

### 1. **Restricted Generic Fallback**

**Before:**
```json
{
  "property": {
    "type": "string"  // ❌ Allowed ANY property name
  },
  "value": {}  // ❌ Allowed ANY structure including nested objects
}
```

**After:**
```json
{
  "property": {
    "type": "string",
    "not": {
      "enum": [
        "attitude_to_risk", "current_value", "gross_annual_salary",
        "annual_amount", "monthly_amount", "employee_contribution_rate",
        // ... 18 specific properties excluded
      ]
    }
  },
  "type": {
    "enum": ["string", "number", "currency", "date", "boolean"]
  },
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

**Impact:**
- ✅ Generic fallback CANNOT use property names that have specific definitions
- ✅ Values MUST be simple types (no nested objects like `{"amount": 165000}`)
- ✅ Type field restricted to standard types only

---

### 2. **Added 4 New Specific SnapshotValue Definitions**

Added for commonly-used timeline fields:

```json
{
  "property": { "const": "employee_contribution_rate" },
  "type": { "const": "number" },
  "value": { "type": "number" }
}
```

```json
{
  "property": { "const": "employer_contribution_rate" },
  "type": { "const": "number" },
  "value": { "type": "number" }
}
```

```json
{
  "property": { "const": "monthly_payment" },
  "type": { "const": "currency" },
  "value": { "type": "number" }
}
```

```json
{
  "property": { "const": "interest_rate" },
  "type": { "const": "number" },
  "value": { "type": "number" }
}
```

**Impact:**
- ✅ Forces consistent field names for contribution rates
- ✅ Forces consistent field names for payments
- ✅ Prevents variants like `monthly_mortgage_payment` vs `approx_monthly_payment`

---

### 3. **Total SnapshotValue Definitions**

**Final count: 19 variants (18 specific + 1 restricted generic)**

#### Specific Properties Enforced:
1. `attitude_to_risk` (was `risk_profile`)
2. `asset_type`
3. `employment_status`
4. `income_type`
5. `category` (expenses)
6. `policy_type`
7. `loan_type`
8. `current_value` (consolidates 6 variants)
9. `gross_annual_salary` (standardized)
10. `annual_amount`
11. `monthly_amount`
12. `objective_summary`
13. `current_state_of_health` (with enum)
14. `smoker_status` (with enum)
15. `employee_contribution_rate` ⭐ NEW
16. `employer_contribution_rate` ⭐ NEW
17. `monthly_payment` ⭐ NEW
18. `interest_rate` ⭐ NEW

---

## 🎯 What This Fixes

### Problem in res2.json:
```json
"values": [
  {
    "type": "currency",
    "label": "annual_gross_income",  // ❌ Wrong field name
    "value": {
      "amount": 165000,  // ❌ Nested object
      "currency": "USD"
    },
    "citation": "..."
  }
]
```

### After Schema Fix (Expected Output):
```json
"values": [
  {
    "property": "gross_annual_salary",  // ✅ Required field with specific name
    "type": "currency",
    "value": 165000,  // ✅ Simple value
    "citation": "..."
  }
]
```

---

### Problem in res1.json:
```json
"risk_profile_timeline": [
  {
    "call_time": "01:01:49",
    "values": [
      {
        "type": "string",  // ❌ Missing "property" field
        "value": "moderate (3 out of 5) risk tolerance...",  // ❌ Free text
        "citation": "..."
      }
    ]
  }
]
```

### After Schema Fix (Expected Output):
```json
"risk_profile_timeline": [
  {
    "call_time": "01:01:49",
    "values": [
      {
        "property": "attitude_to_risk",  // ✅ Required field
        "type": "string",
        "value": "moderately_adventurous",  // ✅ Enum value
        "citation": "..."
      }
    ]
  }
]
```

---

## 📊 Schema Validation Results

```
✅ Schema is valid JSON
✅ 19 SnapshotValue variants defined
✅ 18 specific property definitions with const names
✅ 1 generic fallback with strict constraints
✅ Generic fallback excludes all 18 specific properties
✅ Generic fallback restricts values to simple types only
```

---

## 🚫 What the Schema Now PREVENTS

### 1. Nested Objects in Values
```json
// ❌ NO LONGER ALLOWED
"value": {
  "amount": 165000,
  "currency": "USD"
}

// ✅ REQUIRED FORMAT
"value": 165000
```

### 2. Using "label" Field
```json
// ❌ NO LONGER ALLOWED
{
  "label": "annual_gross_income",
  "type": "currency",
  "value": 165000
}

// ✅ REQUIRED FORMAT
{
  "property": "gross_annual_salary",
  "type": "currency",
  "value": 165000
}
```

### 3. Missing "property" Field
```json
// ❌ NO LONGER ALLOWED (will fail validation)
{
  "type": "string",
  "value": "moderate risk",
  "citation": "..."
}

// ✅ REQUIRED FORMAT
{
  "property": "attitude_to_risk",
  "type": "string",
  "value": "moderately_adventurous",
  "citation": "..."
}
```

### 4. Using Generic Fallback for Defined Properties
```json
// ❌ NO LONGER ALLOWED (excluded by "not" constraint)
{
  "property": "current_value",  // This is a defined property
  "type": "string",
  "value": "59000",
  "citation": "..."
}

// ✅ MUST USE SPECIFIC DEFINITION
{
  "property": "current_value",
  "type": "currency",
  "value": 59000,
  "citation": "..."
}
```

### 5. Free-Form Risk Assessment Text
```json
// ❌ NO LONGER ALLOWED
{
  "property": "attitude_to_risk",
  "type": "string",
  "value": "moderate (3 out of 5) risk tolerance; prepared to take...",
  "citation": "..."
}

// ✅ MUST USE ENUM VALUE
{
  "property": "attitude_to_risk",
  "type": "string",
  "value": "moderately_adventurous",
  "citation": "..."
}
```

---

## 🧪 Testing Required

### 1. Re-run Extractions
Extract both transcripts again with the fixed schema:
```bash
python3 your_extraction_script.py --schema start/schema2.json
```

### 2. Verify Fixes
Check that new outputs have:
- ✅ All timeline values include `property` field
- ✅ No nested objects in values
- ✅ Enum values used where defined
- ✅ Consistent field names across transcripts

### 3. Run Stability Analysis
```bash
python3 combine_schema_examples.py
python3 analyze_schema_stability.py
```

Expected improvements:
- Overlap should increase from 21.2% to 50-60%+
- Fewer unique field variants
- Consistent use of standardized property names

---

## 📝 Key Takeaways

### Why These Fixes Matter:

1. **`property` field is MANDATORY** - Without it, LLM generates loose unstructured data
2. **Simple values only** - Nested objects defeat the purpose of structured output
3. **Specific definitions win** - Generic fallback should be last resort
4. **Enum constraints matter** - Free text creates inconsistency

### Schema Design Principles Applied:

1. ✅ **Be explicit, not permissive** - Generic fallback now has strict constraints
2. ✅ **Exclude what you define** - Generic fallback excludes all specific properties
3. ✅ **Constrain value types** - No more nested objects allowed
4. ✅ **Force consistency** - 18 specific property names are now enforced

---

## 🎯 Expected Results After Re-extraction

### Before (Current):
- Missing `property` fields everywhere
- Nested value objects
- Free-form risk text
- Inconsistent field names
- 21.2% overlap between files

### After (Expected):
- All timeline values have `property` field
- Simple value types only
- Enum values for risk, health, etc.
- Consistent field names
- 50-60%+ overlap between files

---

## ⚠️ Breaking Changes

These schema changes are **breaking** - old outputs won't validate:

1. ❌ Old outputs with missing `property` fields will fail
2. ❌ Old outputs with nested values will fail
3. ❌ Old outputs using `label` instead of `property` will fail

**Migration:** Re-run all extractions with the new schema. Don't try to patch old outputs.

