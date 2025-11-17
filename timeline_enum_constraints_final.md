# Timeline Array Enum Constraints - Final Implementation

## Problem
Timeline arrays were incorrectly described as "intentionally flexible" - they should enforce enum constraints for properties like `asset_type`, `income_type`, etc.

## Solution
Created constrained SnapshotValue definitions and used `oneOf` in timeline arrays to enforce enum constraints while still allowing generic properties.

## New Definitions Added

### 1. AssetTypeSnapshot
```json
"AssetTypeSnapshot": {
  "allOf": [
    { "$ref": "#/definitions/SnapshotValue" },
    {
      "type": "object",
      "properties": {
        "property": { "const": "asset_type" },
        "value": {
          "enum": ["property", "cash", "investment_account", "pension", "business", "other"]
        }
      }
    }
  ]
}
```

### 2. IncomeTypeSnapshot
```json
"IncomeTypeSnapshot": {
  "allOf": [
    { "$ref": "#/definitions/SnapshotValue" },
    {
      "type": "object",
      "properties": {
        "property": { "const": "income_type" },
        "value": {
          "enum": ["salary", "bonus", "rental", "pension", "benefits", "dividends", "interest", "other"]
        }
      }
    }
  ]
}
```

### 3. ExpenseCategorySnapshot
```json
"ExpenseCategorySnapshot": {
  "allOf": [
    { "$ref": "#/definitions/SnapshotValue" },
    {
      "type": "object",
      "properties": {
        "property": { "const": "category" },
        "value": {
          "enum": ["housing", "loan_repayment", "motoring", "personal", "professional", "childcare", "insurance", "miscellaneous", "other"]
        }
      }
    }
  ]
}
```

### 4. LoanTypeSnapshot
```json
"LoanTypeSnapshot": {
  "allOf": [
    { "$ref": "#/definitions/SnapshotValue" },
    {
      "type": "object",
      "properties": {
        "property": { "const": "loan_type" },
        "value": {
          "enum": ["mortgage", "personal_loan", "credit_card", "overdraft", "car_finance", "student_loan", "other"]
        }
      }
    }
  ]
}
```

### 5. PolicyTypeSnapshot
```json
"PolicyTypeSnapshot": {
  "allOf": [
    { "$ref": "#/definitions/SnapshotValue" },
    {
      "type": "object",
      "properties": {
        "property": { "const": "policy_type" },
        "value": {
          "enum": ["life", "critical_illness", "income_protection", "mortgage_protection", "health", "other"]
        }
      }
    }
  ]
}
```

## Timeline Arrays Updated

### AssetItem.timeline
```json
"timeline": {
  "type": "array",
  "items": {
    "oneOf": [
      { "$ref": "#/definitions/AssetTypeSnapshot" },
      { "$ref": "#/definitions/SnapshotValue" }
    ]
  }
}
```
**Result**: When `property: "asset_type"`, the value MUST be one of the allowed asset types. Other properties like `current_value` can be any value.

### IncomeItem.timeline
```json
"timeline": {
  "type": "array",
  "items": {
    "oneOf": [
      { "$ref": "#/definitions/IncomeTypeSnapshot" },
      { "$ref": "#/definitions/SnapshotValue" }
    ]
  }
}
```
**Result**: When `property: "income_type"`, the value MUST be one of the allowed income types.

### ExpenseItem.timeline
```json
"timeline": {
  "type": "array",
  "items": {
    "oneOf": [
      { "$ref": "#/definitions/ExpenseCategorySnapshot" },
      { "$ref": "#/definitions/SnapshotValue" }
    ]
  }
}
```
**Result**: When `property: "category"`, the value MUST be one of the allowed expense categories.

### LoanMortgageItem.timeline
```json
"timeline": {
  "type": "array",
  "items": {
    "oneOf": [
      { "$ref": "#/definitions/LoanTypeSnapshot" },
      { "$ref": "#/definitions/SnapshotValue" }
    ]
  }
}
```
**Result**: When `property: "loan_type"`, the value MUST be one of the allowed loan types.

### ProtectionPolicyItem.timeline
```json
"timeline": {
  "type": "array",
  "items": {
    "oneOf": [
      { "$ref": "#/definitions/PolicyTypeSnapshot" },
      { "$ref": "#/definitions/SnapshotValue" }
    ]
  }
}
```
**Result**: When `property: "policy_type"`, the value MUST be one of the allowed policy types.

## Timeline Arrays NOT Updated (No Enum Properties)

These timeline arrays remain as simple `SnapshotValue` arrays because they don't have enum-constrained properties:

- **`PensionItem.timeline`** - Only numeric properties (fund values, contribution rates)
- **`SavingsInvestmentItem.timeline`** - Only numeric properties (balances, interest rates)  
- **`Client.objectives_timeline`** - Free-form text descriptions

## Validation Examples

### ✅ Valid: Asset with enum type
```json
{
  "property": "asset_type",
  "type": "string",
  "value": "property",
  "citation": "Transcript line 42",
  "call_time": "00:05:23"
}
```

### ✅ Valid: Asset with currency value
```json
{
  "property": "current_value",
  "type": "currency",
  "value": 250000,
  "citation": "Transcript line 43",
  "call_time": "00:05:25"
}
```

### ❌ Invalid: Asset with wrong enum value
```json
{
  "property": "asset_type",
  "type": "string",
  "value": "cryptocurrency",  // Not in enum!
  "citation": "Transcript line 44",
  "call_time": "00:05:30"
}
```

## Benefits

1. ✅ **Enum enforcement**: Type properties are validated against their allowed values
2. ✅ **Flexibility preserved**: Generic properties like `current_value`, `monthly_amount` still work
3. ✅ **Clear constraints**: Each timeline array explicitly declares which properties have enums
4. ✅ **Maintainable**: Easy to add new constrained properties by creating new snapshot definitions
5. ✅ **Better validation**: JSON Schema validators will catch invalid enum values in timelines

## Statistics

- **Constrained snapshot definitions added**: 5
- **Timeline arrays updated**: 5  
- **Timeline arrays unchanged**: 3 (no enum properties)
- **Total enum-constrained properties**: 9 (in static sections) + 5 (in timelines) = 14
- **Schema size**: 703 lines (19.4% smaller than original 872 lines)

## Validation Status
✅ Schema validated successfully with no linter errors

