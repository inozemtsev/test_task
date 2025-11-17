# Enum Constraints Added Using `allOf`

## Summary
Added `allOf` pattern to enforce enum constraints at higher levels throughout the schema, replacing the complex `oneOf` approach.

## Pattern Used

```json
"field_name": {
  "allOf": [
    { "$ref": "#/definitions/ScalarFact" },  // or SnapshotValue
    {
      "type": "object",
      "properties": {
        "value": {
          "type": "string",
          "enum": ["option1", "option2", "option3"]
        }
      }
    }
  ]
}
```

## All Locations with Enum Constraints

### 1. Client.personal_details
- **`marital_status`** (already existed)
  - Enum: `["single", "married", "civil_partnership", "divorced", "widowed", "separated", "cohabiting", "other"]`

### 2. Client.employment_details
- **`employment_status`** (already existed)
  - Enum: `["employed", "self_employed", "company_director", "unemployed", "retired", "student", "homemaker", "other"]`

### 3. Client.health_details
- **`current_state_of_health`** ✨ ADDED
  - Enum: `["excellent", "good", "fair", "poor", "not_discussed"]`
  
- **`smoker_status`** ✨ ADDED
  - Enum: `["smoker", "non_smoker", "former_smoker", "not_discussed"]`

### 4. Client.risk_profile_timeline
- **Items** (already existed, uses SnapshotValue)
  - Property: `"risk_profile"`
  - Enum: `["very_cautious", "cautious", "balanced", "moderately_adventurous", "adventurous", "very_adventurous"]`

### 5. AssetItem.static
- **`asset_type`** (already existed)
  - Enum: `["property", "cash", "investment_account", "pension", "business", "other"]`

### 6. IncomeItem.static
- **`income_type`** (already existed)
  - Enum: `["salary", "bonus", "rental", "pension", "benefits", "dividends", "interest", "other"]`

### 7. ExpenseItem.static
- **`category`** (already existed)
  - Enum: `["housing", "loan_repayment", "motoring", "personal", "professional", "childcare", "insurance", "miscellaneous", "other"]`

### 8. LoanMortgageItem.static
- **`loan_type`** (already existed)
  - Enum: `["mortgage", "personal_loan", "credit_card", "overdraft", "car_finance", "student_loan", "other"]`

### 9. ProtectionPolicyItem.static
- **`policy_type`** (already existed)
  - Enum: `["life", "critical_illness", "income_protection", "mortgage_protection", "health", "other"]`

## Timeline Arrays with Enum Constraints

Timeline arrays now use `oneOf` to enforce enum constraints for specific property types while allowing generic properties:

### Structure
```json
"timeline": {
  "items": {
    "oneOf": [
      { "$ref": "#/definitions/SpecificTypeSnapshot" },  // Enum-constrained
      { "$ref": "#/definitions/SnapshotValue" }          // Generic fallback
    ]
  }
}
```

### Constrained Snapshot Definitions
- **`AssetTypeSnapshot`** - Used in `AssetItem.timeline`
  - Property: `asset_type`
  - Enum: `["property", "cash", "investment_account", "pension", "business", "other"]`

- **`IncomeTypeSnapshot`** - Used in `IncomeItem.timeline`
  - Property: `income_type`
  - Enum: `["salary", "bonus", "rental", "pension", "benefits", "dividends", "interest", "other"]`

- **`ExpenseCategorySnapshot`** - Used in `ExpenseItem.timeline`
  - Property: `category`
  - Enum: `["housing", "loan_repayment", "motoring", "personal", "professional", "childcare", "insurance", "miscellaneous", "other"]`

- **`LoanTypeSnapshot`** - Used in `LoanMortgageItem.timeline`
  - Property: `loan_type`
  - Enum: `["mortgage", "personal_loan", "credit_card", "overdraft", "car_finance", "student_loan", "other"]`

- **`PolicyTypeSnapshot`** - Used in `ProtectionPolicyItem.timeline`
  - Property: `policy_type`
  - Enum: `["life", "critical_illness", "income_protection", "mortgage_protection", "health", "other"]`

### Timeline Arrays Without Type Constraints
These timelines only contain numerical/currency properties (no enum types):
- `PensionItem.timeline` - Only numeric properties (fund values, contribution rates)
- `SavingsInvestmentItem.timeline` - Only numeric properties (balances, interest rates)
- `Client.objectives_timeline` - Free-form objective descriptions

### Generic Properties in Timelines
Timeline arrays can also contain generic properties like:
- `current_value` (currency)
- `monthly_amount` / `annual_amount` (currency)
- `monthly_payment` (currency)
- `interest_rate` (number)
- `employee_contribution_rate` / `employer_contribution_rate` (number)
- Any other dynamic numerical or string properties

## Benefits

1. ✅ **Type safety**: Values are validated against specific enums
2. ✅ **Maintainability**: Easy to see and modify enum values
3. ✅ **Clarity**: Constraints are applied where the property is used
4. ✅ **Flexibility**: Generic definitions remain reusable
5. ✅ **Better validation**: JSON Schema validators will catch invalid enum values

## Validation Status
✅ Schema validated successfully with no linter errors

