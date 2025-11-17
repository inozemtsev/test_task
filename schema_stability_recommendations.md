# Schema Stability Recommendations

## ⚠️ Critical Context

**Extraction Method:** Structured Output via JSON Schema (NO explicit prompt)
- LLM is constrained purely by the JSON schema structure
- Inconsistencies indicate the **schema itself is too flexible/ambiguous**
- Solution: Make schema MORE STRICT, remove optionality where causing issues

## Executive Summary

**Current Schema Stability: LOW (21.2% overlap)**
- Only 18 out of 85 fields are consistently captured across both transcripts
- 59 fields appear in only one file, indicating **schema allows too much flexibility**
- Average nesting depth disparity: 6.5 levels vs 4.7 levels
- **Root Cause:** Schema has redundant/similar fields that LLM chooses between inconsistently

---

## 🧠 Understanding the Real Problem

### Why 21% Overlap with Structured Output?

With **no explicit prompt**, the LLM's behavior is ENTIRELY controlled by the schema. Low overlap means:

1. **Schema has redundant fields** → LLM picks randomly between `risk_profile` vs `attitude_to_risk`
2. **Schema is too flexible** → Too many optional fields, LLM omits inconsistently  
3. **No naming constraints** → LLM matches field names to transcript wording (`annual` vs `monthly`)
4. **Unclear field semantics** → 6 different "current value" fields confuse the model

### The Fix: Make Schema MORE Opinionated

❌ **Wrong approach:** "Add more fields to cover all cases"  
✅ **Right approach:** "Delete redundant fields, keep only one canonical version"

❌ **Wrong approach:** "Make everything optional so LLM has flexibility"  
✅ **Right approach:** "Make core fields required with `null` or `"not_discussed"` as fallback"

❌ **Wrong approach:** "Let LLM choose appropriate field names"  
✅ **Right approach:** "One concept = one field name. No variations."

---

## 🔴 HIGH PRIORITY Issues

### 1. Risk Assessment Field Inconsistency

**Problem:**
- `clients[].risk_profile_timeline[].values[].risk_profile` (file 1)
- `clients[].risk_profile_timeline[].values[].attitude_to_risk` (file 2)

These represent the **same concept** but use different field names.

**Examples:**
- File 1: "Moderate (around 3 out of 5) – willing to take some risk but..."
- File 2: "moderately_adventurous"

**Solution:**
```json
{
  "field_name": "attitude_to_risk",  // Use this standard name
  "type": "string",
  "enum": [
    "very_cautious",
    "cautious", 
    "balanced",
    "moderately_adventurous",
    "adventurous",
    "very_adventurous"
  ],
  "description": "Client's standardized attitude to investment risk"
}
```

**Root Cause:** Schema defines BOTH fields as valid options, LLM randomly chooses between them.

**Action (Schema Changes):**
- ✅ **DELETE** `risk_profile` field from schema entirely
- ✅ **KEEP ONLY** `attitude_to_risk` field
- ✅ **ADD** strict enum constraint in schema:
  ```json
  "enum": ["very_cautious", "cautious", "balanced", "moderately_adventurous", "adventurous", "very_adventurous"]
  ```
- ✅ Make field **required** (not optional) if this data is critical

---

### 2. Current Value Field Variants (6 different fields!)

**Problem:**
Multiple fields representing pension/asset current values:
- `pensions[].timeline[].values[].current_fund_value` (exact)
- `pensions[].timeline[].values[].approx_current_value` (approximate)
- `pensions[].timeline[].values[].approx_current_value_initial` (specific point in time)
- `pensions[].timeline[].values[].approx_current_value_updated` (specific point in time)
- `pensions[].timeline[].timeline[].values[].current_fund_value` (nested)
- `pensions[].timeline[].timeline[].values[].current_fund_value_estimate` (estimated)

**Solution:**
```json
{
  "current_value": {
    "type": "currency",
    "description": "Current fund value"
  },
  "value_as_of_date": {
    "type": "date",
    "description": "Date when value was stated/estimated"
  },
  "is_estimate": {
    "type": "boolean",
    "description": "Whether value is estimated vs exact",
    "default": false
  }
}
```

**Root Cause:** Schema has 6 different optional fields for the same concept. LLM picks whichever seems "closest" to transcript wording.

**Action (Schema Changes):**
- ✅ **DELETE** all variant fields: `approx_current_value`, `approx_current_value_initial`, `approx_current_value_updated`, `current_fund_value_estimate`
- ✅ **KEEP ONLY** `current_value` as the standard field name
- ✅ **ADD** optional metadata fields: `value_as_of_date` (date), `is_estimate` (boolean)
- ✅ Result: 6 fields → 1 field + 2 optional metadata fields

---

## 🟡 MEDIUM PRIORITY Issues

### 3. Annual vs Monthly Amount Inconsistency

**Problem:**
- File 1 uses: `annual_amount`, `gross_annual_amount`, `expected_annual_amount`
- File 2 uses: `monthly_amount`, `current_year_expected_bonus`

Different transcripts capture amounts in different time periods.

**Examples:**
- Expenses: annual_amount = 8000 vs monthly_amount = 2000
- Income: gross_annual_amount = 43000 vs gross_annual_salary = 78000

**Solution:**
```json
{
  "amount": {
    "type": "currency",
    "description": "The amount"
  },
  "period": {
    "type": "string",
    "enum": ["annual", "monthly", "weekly", "one_time"],
    "description": "Period for the amount"
  }
}
```

**Alternative Solution (more explicit):**
```json
{
  "annual_amount": {"type": "currency", "optional": true},
  "monthly_amount": {"type": "currency", "optional": true},
  // LLM should populate at least one
}
```

**Root Cause:** Schema defines these as separate optional fields in different contexts. LLM uses whichever is mentioned first in transcript.

**Action (Schema Changes):**
- ✅ **KEEP BOTH** `annual_amount` AND `monthly_amount` fields
- ✅ Make both optional in schema definition
- ✅ **ADD** schema constraint: `"minProperties": 1` (at least one must be present)
- ✅ **ALTERNATIVE:** Add single `amount` field + required `period` enum field ("annual"|"monthly"|"weekly")

---

### 4. Income Field Redundancy

**Problem:**
Multiple similar fields for gross income:
- `gross_annual_amount` (73.7% similar)
- `gross_annual_salary` (73.7% similar)
- `gross_annual_salary_including_car_allowance` (51.6% similar)

**Solution:**
```json
{
  "gross_annual_salary": {
    "type": "currency",
    "description": "Base gross annual salary"
  },
  "additional_compensation": [
    {
      "type": "string",
      "enum": ["bonus", "car_allowance", "commission", "overtime", "other"],
      "amount": "currency",
      "description": "string"
    }
  ]
}
```

**Root Cause:** Schema has 3 similar fields for gross income. LLM doesn't know which to use.

**Action (Schema Changes):**
- ✅ **DELETE** `gross_annual_amount` and `gross_annual_salary_including_car_allowance` from schema
- ✅ **KEEP** `gross_annual_salary` as the base salary field
- ✅ **ADD** separate `additional_compensation` array with structured sub-schema:
  ```json
  "additional_compensation": {
    "type": "array",
    "items": {
      "type": {"enum": ["bonus", "car_allowance", "commission", "overtime", "other"]},
      "amount": "currency",
      "period": {"enum": ["annual", "monthly"]}
    }
  }
  ```

---

### 5. Health Details Not Consistently Captured

**Problem:**
Health fields only in file 2:
- `clients[].health_details.current_state_of_health`
- `clients[].health_details.has_will`
- `clients[].health_details.smoker_status`

**Examples:**
- Most values are: "Not discussed", "Not provided", "Not mentioned"

**Solution:**
Keep these fields but make them **explicitly optional** and always present in schema.

**Root Cause:** Fields are defined in schema but marked as deeply optional/nullable. LLM omits entire object when not explicitly mentioned.

**Action (Schema Changes):**
- ✅ **KEEP** all health fields in schema definition
- ✅ Mark as `"required": false` at field level
- ✅ **ADD** enum value `"not_discussed"` as valid option:
  ```json
  "current_state_of_health": {
    "enum": ["excellent", "good", "fair", "poor", "not_discussed"]
  },
  "smoker_status": {
    "enum": ["smoker", "non_smoker", "former_smoker", "not_discussed"]
  }
  ```
- ⚠️ **NOTE:** Fields appearing in only one file suggests they may be TOO optional - consider making required with "not_discussed" as fallback

---

### 6. Contact Information Not Consistently Extracted

**Problem:**
Contact fields only in file 2:
- `clients[].personal_details.email`
- `clients[].personal_details.mobile_phone`

Examples show: "advisor confirms having his number" but actual number not extracted.

**Root Cause:** Fields exist in schema but are too optional. LLM omits when contact details aren't explicitly stated.

**Action (Schema Changes):**
- ✅ **KEEP** fields in schema definition (email, mobile_phone)
- ✅ Make fields **nullable** in schema: `"type": ["string", "null"]`
- ✅ Set `"default": null` so fields always appear in output
- ⚠️ **IMPORTANT:** Don't let LLM fill with descriptive text like "Not stated" - enforce `null` or actual value only
- 💡 **ALTERNATIVE:** Make required with pattern validation (email regex, phone regex) to force real extraction

---

## 🟢 LOW PRIORITY Issues

### 7. Complex Nested Timeline Structure

**Problem:**
`pensions[].timeline[].timeline[].values[]` creates 8-level nesting (depth 8).

File 1 has significantly deeper nesting (6.5 avg) vs File 2 (4.7 avg).

**Current Structure (File 1):**
```
pensions[]
  └── timeline[]
      └── timeline[]
          └── values[]
              └── current_fund_value
```

**Proposed Flattened Structure:**
```
pensions[]
  └── accounts[]  // Instead of timeline[].timeline[]
      └── static (metadata)
      └── timeline[]
          └── values[]
              └── current_fund_value
```

**Action:**
- ⚠️ Consider for future refactoring (breaking change)
- ✅ For now: Document that nested timelines should be avoided
- ✅ Encourage flatter structure in new schema versions

---

## 📊 Additional Findings

### Structural Issues

1. **Savings Structure Inconsistency:**
   - File 1: `pensions[].savings_and_investments[]` (savings nested under pensions!)
   - File 2: `savings_and_investments[]` (top-level, correct placement)
   
   **Action:** Move savings to top-level, separate from pensions.

2. **Mortgage Payment Duplication:**
   - `assets[].timeline[].values[].monthly_mortgage_payment`
   - `loans_and_mortgages[].timeline[].values[].approx_monthly_payment`
   
   **Action:** Only store in `loans_and_mortgages[]` (single source of truth)

3. **Employer Field Split:**
   - File 1: `clients[].employment_details.employer` = "Kroger (St Peter's store)"
   - File 2: `incomes[].static.employer_or_payer` = "Insurance brokerage"
   
   **Action:** Keep `employer` in `employment_details`, don't duplicate in `incomes[]`

---

## 🎯 Implementation Plan

### Phase 1: Critical Fixes (Immediate)
1. ✅ Consolidate `risk_profile` / `attitude_to_risk` → Use `attitude_to_risk` with strict enum
2. ✅ Consolidate 6 current value variants → Use `current_value` + metadata
3. ✅ Standardize income fields → Use `gross_annual_salary` + `additional_compensation[]`

**Expected Impact:** Reduce unique fields from 59 to ~45, increase overlap from 21.2% to ~35%

### Phase 2: Standardization (Next Sprint)
4. ✅ Support both annual and monthly amounts (make both optional)
5. ✅ Make health fields explicitly optional with "not_discussed" default
6. ✅ Standardize contact information handling (use null, not descriptive text)

**Expected Impact:** Increase overlap to ~50%, improve extraction consistency

### Phase 3: Structural Refactoring (Future)
7. ⚠️ Flatten nested timeline structures
8. ⚠️ Move savings_and_investments to top-level
9. ⚠️ Remove duplicate mortgage payment fields

**Expected Impact:** Cleaner schema, easier to maintain, ~60-70% overlap target

---

## 🛠️ Concrete Schema Modifications

### Example: Fixing Risk Profile Duplication

**BEFORE (schema2.json has both):**
```json
{
  "clients": {
    "type": "array",
    "items": {
      "risk_profile_timeline": [{
        "values": [{
          "risk_profile": {"type": "string"},  // ❌ Remove this
          "attitude_to_risk": {"type": "string"}  // ❌ And this variant
        }]
      }]
    }
  }
}
```

**AFTER (consolidated):**
```json
{
  "clients": {
    "type": "array",
    "items": {
      "risk_profile_timeline": [{
        "values": [{
          "attitude_to_risk": {
            "type": "string",
            "enum": [
              "very_cautious",
              "cautious", 
              "balanced",
              "moderately_adventurous",
              "adventurous",
              "very_adventurous"
            ],
            "description": "Standardized risk attitude assessment"
          }
        }]
      }]
    }
  }
}
```

### Example: Fixing Current Value Chaos

**BEFORE (6 variants in schema):**
```json
{
  "current_fund_value": {"type": "number"},
  "approx_current_value": {"type": "number"},
  "approx_current_value_initial": {"type": "number"},
  "approx_current_value_updated": {"type": "number"},
  "current_fund_value_estimate": {"type": "string"}
}
```

**AFTER (1 field + metadata):**
```json
{
  "current_value": {
    "type": "number",
    "description": "Current fund value in currency"
  },
  "value_as_of_date": {
    "type": ["string", "null"],
    "format": "date",
    "default": null
  },
  "is_estimate": {
    "type": "boolean",
    "default": false
  }
}
```

---

## 📋 Schema Update Checklist

Before releasing updated schema:

- [ ] **Identify** all redundant field variations to consolidate
- [ ] **Delete** unnecessary fields from schema definition  
- [ ] **Add** strict enum constraints for standardized fields
- [ ] **Set** appropriate `required` vs `optional` flags
- [ ] **Add** `"default": null` for optional fields that should always appear
- [ ] **Test** updated schema with both existing transcript files
- [ ] **Verify** overlap percentage improves (run `analyze_schema_stability.py`)
- [ ] **Create** migration guide for existing data if breaking changes
- [ ] **Document** field consolidations and removals in changelog
- [ ] **Update** any downstream systems, queries, or visualization code

---

## 🎓 Best Practices for Schema Design (Structured Output)

### 1. **Eliminate Redundant Field Choices**
   - ❌ **BAD:** Schema has both `risk_profile` AND `attitude_to_risk`
   - ✅ **GOOD:** Schema has ONLY `attitude_to_risk` (one field per concept)
   - **Why:** LLM will randomly pick between similar fields, causing inconsistency

### 2. **Use Strict Enums**
   - ❌ **BAD:** Free-text fields like `"Moderate (around 3 out of 5)"`
   - ✅ **GOOD:** Enum: `["very_cautious", "cautious", "balanced", "moderately_adventurous", "adventurous"]`
   - **Why:** Forces consistency across all extractions

### 3. **Avoid Naming Variations**
   - ❌ **BAD:** `current_value`, `approx_current_value`, `current_fund_value`, `approx_current_value_initial`
   - ✅ **GOOD:** Single field `current_value` + metadata boolean `is_estimate`
   - **Why:** LLM picks whichever name seems closest to transcript wording

### 4. **Handle Optional Data Explicitly**
   - ❌ **BAD:** Field completely absent from output if not mentioned
   - ✅ **GOOD:** Field present with `null` or enum value `"not_discussed"`
   - **Why:** Makes it clear data was considered but not found vs field forgotten

### 5. **Constrain Flexibility**
   - ❌ **BAD:** Many optional fields, LLM chooses which to populate
   - ✅ **GOOD:** Required fields with `null` allowed, or strict `minProperties` constraints
   - **Why:** Less optionality = more consistency

### 6. **Time Period Standardization**
   - ✅ **Option A:** Support BOTH `annual_amount` and `monthly_amount` with `"minProperties": 1`
   - ✅ **Option B:** Single `amount` + required `period` enum ("annual"|"monthly"|"weekly")
   - **Why:** LLM needs clear guidance on which field to use

### 7. **Limit Nesting Depth**
   - ❌ **BAD:** `pensions[].timeline[].timeline[].values[]` (depth 8)
   - ✅ **GOOD:** `pensions[].accounts[].timeline[].values[]` (depth 6, clearer semantics)
   - **Why:** Deep nesting makes schema harder for LLM to navigate correctly

### 8. **Schema Testing Strategy**
   - Run `analyze_schema_stability.py` on every schema change
   - Test with 2-3 diverse transcripts before deploying
   - Track overlap percentage over time (target: >60%)
   - Any field appearing in <50% of outputs is a candidate for consolidation

---

## 📈 Success Metrics

**Current State:**
- Schema overlap: 21.2%
- Unique fields: 59
- High priority issues: 2
- Average nesting: 5.6 levels

**Target State (6 months):**
- Schema overlap: >60%
- Unique fields: <30
- High priority issues: 0
- Average nesting: <5 levels

**Tracking:**
Run `python3 analyze_schema_stability.py` monthly and track metrics.

---

## 💡 TL;DR - The Core Issue

### The Problem
Your schema currently has **redundant/overlapping fields** for the same concepts:
- `risk_profile` AND `attitude_to_risk` (same thing, 2 names)
- `current_fund_value`, `approx_current_value`, `approx_current_value_initial`, `approx_current_value_updated` (same thing, 6 names!)
- `gross_annual_amount` AND `gross_annual_salary` (same thing, 2 names)

When using **structured output without explicit prompts**, the LLM randomly picks between these variants based on transcript wording. This creates 21% overlap (terrible).

### The Solution
**Delete redundant fields. Keep only ONE canonical name per concept.**

### Immediate Actions
1. Open `schema2.json`
2. Search for `risk_profile` and `attitude_to_risk` - delete one, keep the other
3. Search for all `current.*value` variants - consolidate to single `current_value`
4. Search for `gross_annual_amount` and `gross_annual_salary` - keep one, delete other
5. Add strict `enum` constraints wherever possible
6. Re-run extractions with cleaned schema
7. Run `python3 analyze_schema_stability.py` to verify improvement

**Expected result:** Overlap increases from 21% → 40-50% immediately, 60-70% after full cleanup.

### Remember
With structured output:
- **More fields ≠ Better** - More fields = More confusion
- **Flexibility ≠ Good** - Flexibility = Inconsistency  
- **One concept = One field name** - No variations, no alternatives

The schema IS the spec. Make it strict, opinionated, and unambiguous.

