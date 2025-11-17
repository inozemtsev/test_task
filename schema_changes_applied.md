# Schema Changes Applied to schema2.json

## Summary

Applied HIGH and MEDIUM priority recommendations from schema stability analysis to improve consistency from **21.2% to target 50-60%** overlap.

---

## ✅ Changes Implemented

### 1. **Risk Assessment Field Consolidation** (HIGH PRIORITY)

**Before:**
- `risk_profile` property with enum values

**After:**
- ✅ Renamed to `attitude_to_risk`
- ✅ Added `moderately_adventurous` to enum
- ✅ Updated description to indicate consolidation

**Impact:** Eliminates confusion between `risk_profile` vs `attitude_to_risk` field names.

```json
"property": { "const": "attitude_to_risk" },
"value": {
  "enum": [
    "very_cautious",
    "cautious",
    "balanced",
    "moderately_adventurous",  // ← Added
    "adventurous",
    "very_adventurous"
  ]
}
```

---

### 2. **Current Value Field Standardization** (HIGH PRIORITY)

**Before:**
- Generic fallback allowed: `current_fund_value`, `approx_current_value`, `approx_current_value_initial`, `approx_current_value_updated`, `current_fund_value_estimate`, etc.

**After:**
- ✅ Added specific `current_value` SnapshotValue definition
- ✅ Included optional metadata fields:
  - `is_estimate` (boolean) - whether value is estimated
  - `value_as_of_date` (date) - when value was stated

**Impact:** Forces LLM to use single standardized field name instead of inventing variants.

```json
{
  "property": { "const": "current_value" },
  "type": { "const": "currency" },
  "value": { "type": "number" },
  "citation": { "type": "string" },
  "is_estimate": { "type": "boolean" },
  "value_as_of_date": { "type": "string", "format": "date" }
}
```

---

### 3. **Income Field Standardization** (MEDIUM PRIORITY)

**Before:**
- Generic fallback allowed: `gross_annual_amount`, `gross_annual_salary`, `gross_annual_salary_including_car_allowance`, etc.

**After:**
- ✅ Added specific `gross_annual_salary` SnapshotValue definition

**Impact:** Standardizes to single field name for base salary.

```json
{
  "property": { "const": "gross_annual_salary" },
  "type": { "const": "currency" },
  "value": { "type": "number" }
}
```

---

### 4. **Annual vs Monthly Amount Support** (MEDIUM PRIORITY)

**Before:**
- Generic fallback allowed both, LLM chose randomly

**After:**
- ✅ Added specific `annual_amount` SnapshotValue definition
- ✅ Added specific `monthly_amount` SnapshotValue definition

**Impact:** Both are now explicitly supported, forcing consistent field names.

```json
// Two separate, explicit definitions
{ "property": { "const": "annual_amount" } }
{ "property": { "const": "monthly_amount" } }
```

---

### 5. **Health Fields Standardization** (MEDIUM PRIORITY)

**Before:**
- Generic fallback allowed free-text like "Not discussed", "Not provided"

**After:**
- ✅ Added `current_state_of_health` with strict enum
- ✅ Added `smoker_status` with strict enum
- ✅ Both include `"not_discussed"` as valid value

**Impact:** Prevents descriptive text, forces enumerated values.

```json
{
  "property": { "const": "current_state_of_health" },
  "value": {
    "enum": ["excellent", "good", "fair", "poor", "not_discussed"]
  }
},
{
  "property": { "const": "smoker_status" },
  "value": {
    "enum": ["smoker", "non_smoker", "former_smoker", "not_discussed"]
  }
}
```

---

### 6. **Objective Summary Standardization**

**Added:**
- ✅ Specific `objective_summary` SnapshotValue definition

**Impact:** Ensures consistent field naming for client objectives.

---

### 7. **Schema Strictness Improvements**

**Changed:**
- ✅ `employment_details.additionalProperties`: `true` → `false`
- ✅ `health_details.additionalProperties`: `true` → `false`

**Impact:** Prevents LLM from adding arbitrary extra fields not in schema.

---

## 📊 Schema Statistics

### SnapshotValue Definitions
- **Total variants:** 15 (was: 8)
- **Specific property definitions:** 14 (was: 7)
- **Generic fallback:** 1 (still available but discouraged)

### Specific Properties Now Enforced:
1. `attitude_to_risk` (renamed from `risk_profile`)
2. `asset_type`
3. `employment_status`
4. `income_type`
5. `category` (expenses)
6. `policy_type`
7. `loan_type`
8. `current_value` (NEW - consolidates 6 variants)
9. `gross_annual_salary` (NEW)
10. `annual_amount` (NEW)
11. `monthly_amount` (NEW)
12. `objective_summary` (NEW)
13. `current_state_of_health` (NEW)
14. `smoker_status` (NEW)

---

## 🎯 Expected Impact

### Before Changes:
- Schema overlap: **21.2%**
- Fields only in file 1: 23
- Fields only in file 2: 36
- Total unique fields: 59

### After Changes (Predicted):
- Schema overlap: **45-55%** (improvement of ~25-30 percentage points)
- Reduction in unique fields: ~20-25 fewer variants
- Most common inconsistencies eliminated

### Key Improvements:
1. ✅ **Risk profile** field name now consistent
2. ✅ **Current value** variants reduced from 6 to 1
3. ✅ **Income** field names standardized
4. ✅ **Health** fields now use enums instead of free text
5. ✅ **Less flexibility** = more consistency

---

## 🧪 Testing Recommendations

### 1. Re-run Extractions
Re-run both transcript extractions with the updated schema:
```bash
# Extract with new schema
python3 your_extraction_script.py --schema start/schema2.json
```

### 2. Re-analyze Stability
Run the stability analysis to verify improvement:
```bash
python3 analyze_schema_stability.py
```

### 3. Expected Results
- Overlap should increase from 21.2% to 45-55%
- Fields like `attitude_to_risk` should now appear in BOTH files
- `current_value` should replace all variants
- Health fields should use enum values consistently

---

## 📋 Still TODO (Future Phases)

### Not Yet Implemented (Breaking Changes):
1. ❌ Remove `employer_or_payer` from incomes (use `employment_details.employer` instead)
2. ❌ Flatten `pensions[].timeline[].timeline[]` structure
3. ❌ Remove duplicate mortgage payment fields
4. ❌ Move `savings_and_investments` out of `pensions` (if nested)

### Reason for Deferral:
These require restructuring existing data and are scheduled for Phase 3 (structural refactoring).

---

## 🔄 Migration Guide

### For Existing Data

If you have existing structured outputs using old field names:

**Risk Profile:**
```python
# Old: "property": "risk_profile"
# New: "property": "attitude_to_risk"
if snapshot['property'] == 'risk_profile':
    snapshot['property'] = 'attitude_to_risk'
```

**Current Value:**
```python
# Old: "property": "approx_current_value"
# New: "property": "current_value", "is_estimate": true
if snapshot['property'] in ['approx_current_value', 'approx_current_value_initial', 
                            'approx_current_value_updated', 'current_fund_value_estimate']:
    snapshot['property'] = 'current_value'
    snapshot['is_estimate'] = True
elif snapshot['property'] == 'current_fund_value':
    snapshot['property'] = 'current_value'
```

**Income:**
```python
# Old: "property": "gross_annual_amount"
# New: "property": "gross_annual_salary"
if snapshot['property'] == 'gross_annual_amount':
    snapshot['property'] = 'gross_annual_salary'
```

---

## ✅ Validation

Schema validated successfully:
- ✅ Valid JSON syntax
- ✅ 15 SnapshotValue variants defined
- ✅ 14 specific property constraints
- ✅ No duplicate property names
- ✅ All enums properly defined

---

## 📝 Notes

- The generic fallback snapshot is still available but now clearly marked as "use only when no specific snapshot type exists"
- LLM should prefer specific snapshot definitions over generic fallback
- Stricter `additionalProperties: false` prevents field proliferation
- All changes are **forward-compatible** (old schemas will still parse, but produce less consistent results)

