# Schema Simplification Changes

## Summary
Simplified `schema2.json` by removing unnecessary nesting and moving enum enforcement to higher levels.

## Changes Made

### 1. **Removed the `TimedSnapshot` wrapper** (was lines 402-423)
   - **Before**: Timeline arrays contained `TimedSnapshot` objects, which had `call_time`, `recorded_at`, and a nested `value` object containing a `SnapshotValue`
   - **After**: Timeline arrays now directly contain `SnapshotValue` objects

### 2. **Simplified `SnapshotValue` definition** (now lines 86-128)
   - **Before**: 315+ lines with a massive `oneOf` containing 18 branches for different property types with embedded enum constraints
   - **After**: Simple 42-line object definition with:
     - `property` (string)
     - `type` (enum: string, number, currency, date, boolean)
     - `value` (any)
     - `citation` (string)
     - `call_time` (optional, HH:MM:SS pattern)
     - `recorded_at` (optional, ISO 8601 datetime)
     - `is_estimate` (optional boolean)
     - `value_as_of_date` (optional date)

### 3. **Moved enum enforcement to usage points**
   - **Example**: `risk_profile_timeline` now uses `allOf` to combine base `SnapshotValue` with specific enum constraints:
     ```json
     "risk_profile_timeline": {
       "type": "array",
       "items": {
         "allOf": [
           { "$ref": "#/definitions/SnapshotValue" },
           {
             "type": "object",
             "properties": {
               "property": { "const": "risk_profile" },
               "value": {
                 "enum": ["very_cautious", "cautious", "balanced", ...]
               }
             }
           }
         ]
       }
     }
     ```

### 4. **Updated all timeline arrays** (8 locations)
   - Changed from: `"items": { "$ref": "#/definitions/TimedSnapshot" }`
   - Changed to: `"items": { "$ref": "#/definitions/SnapshotValue" }`
   - Affected items:
     - `AssetItem.timeline`
     - `IncomeItem.timeline`
     - `ExpenseItem.timeline`
     - `PensionItem.timeline`
     - `SavingsInvestmentItem.timeline`
     - `LoanMortgageItem.timeline`
     - `ProtectionPolicyItem.timeline`
     - `Client.objectives_timeline`

## Benefits

1. **Simpler structure**: No unnecessary array wrapping in timedSnapshots
2. **Easier validation**: Enum constraints applied at appropriate levels using `allOf`
3. **More maintainable**: Reduced from ~315 lines to ~42 lines for core snapshot definition
4. **Clearer semantics**: Timeline arrays are directly arrays of snapshot values
5. **Better extensibility**: Easy to add new properties without modifying `SnapshotValue` definition

## File Size Changes
- **Original (with complex oneOf)**: 872 lines
- **After simplification**: 577 lines (33.8% reduction)
- **After adding enum constraints**: 703 lines
- **Final reduction**: 169 lines (19.4% smaller than original)

The final version is larger than the fully simplified version because we added back 5 constrained snapshot definitions and updated 5 timeline arrays to use `oneOf`. However, it's still much cleaner than the original 315-line `oneOf` with 18 branches, and the constraints are now properly enforced at the timeline level.

## Data Structure Example

### Before:
```json
"timeline": [
  {
    "call_time": "00:05:23",
    "recorded_at": "2024-01-15T10:05:23Z",
    "value": {
      "property": "current_value",
      "type": "currency",
      "value": 250000,
      "citation": "Transcript line 45"
    }
  }
]
```

### After:
```json
"timeline": [
  {
    "property": "current_value",
    "type": "currency",
    "value": 250000,
    "citation": "Transcript line 45",
    "call_time": "00:05:23",
    "recorded_at": "2024-01-15T10:05:23Z"
  }
]
```

Much flatter and cleaner!

