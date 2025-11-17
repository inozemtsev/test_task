#!/usr/bin/env python3
"""
Analyze schema stability by identifying potential redundancies and inconsistencies
in fields that appear in only one file.
"""

import json
from typing import Dict, List, Set, Tuple
from difflib import SequenceMatcher


def similarity_ratio(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def get_field_basename(path: str) -> str:
    """Extract the final field name from a path"""
    # Remove array notation and get last part
    parts = path.replace('[]', '').split('.')
    return parts[-1] if parts else path


def get_field_parent(path: str) -> str:
    """Extract the parent path (everything before the last field)"""
    parts = path.split('.')
    return '.'.join(parts[:-1]) if len(parts) > 1 else ''


def analyze_schema_stability(json_path: str):
    """Main analysis function"""
    
    # Load the combined data
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    file1_path = data['example_files'][0]
    file2_path = data['example_files'][1]
    file1_name = file1_path.split('/')[-1]
    file2_name = file2_path.split('/')[-1]
    
    # Separate fields by file
    fields_in_file1 = set()
    fields_in_file2 = set()
    fields_in_both = set()
    
    for path, field_data in data['fields'].items():
        has_file1 = any(file1_path in ex['source'] for ex in field_data['examples'])
        has_file2 = any(file2_path in ex['source'] for ex in field_data['examples'])
        
        if has_file1:
            fields_in_file1.add(path)
        if has_file2:
            fields_in_file2.add(path)
        if has_file1 and has_file2:
            fields_in_both.add(path)
    
    only_in_file1 = sorted(fields_in_file1 - fields_in_file2)
    only_in_file2 = sorted(fields_in_file2 - fields_in_file1)
    
    print("=" * 80)
    print("SCHEMA STABILITY ANALYSIS")
    print("=" * 80)
    print()
    
    # Analysis 1: Similar field names across files
    print("ANALYSIS 1: POTENTIAL DUPLICATE/REDUNDANT FIELDS")
    print("=" * 80)
    print("Fields with similar names that might represent the same concept:")
    print()
    
    duplicates_found = []
    
    for field1 in only_in_file1:
        basename1 = get_field_basename(field1)
        parent1 = get_field_parent(field1)
        
        for field2 in only_in_file2:
            basename2 = get_field_basename(field2)
            parent2 = get_field_parent(field2)
            
            # Check if they have the same parent path
            if parent1 == parent2:
                # Check field name similarity
                sim = similarity_ratio(basename1, basename2)
                if sim > 0.5:  # More than 50% similar
                    duplicates_found.append({
                        'field1': field1,
                        'field2': field2,
                        'similarity': sim,
                        'file1': file1_name,
                        'file2': file2_name
                    })
    
    if duplicates_found:
        duplicates_found.sort(key=lambda x: x['similarity'], reverse=True)
        for dup in duplicates_found:
            print(f"Similarity: {dup['similarity']:.1%}")
            print(f"  📄 {dup['file1']}: {dup['field1']}")
            print(f"  📄 {dup['file2']}: {dup['field2']}")
            
            # Show example values
            field1_examples = data['fields'][dup['field1']]['examples']
            field2_examples = data['fields'][dup['field2']]['examples']
            
            if field1_examples:
                print(f"     Example from {dup['file1']}: {field1_examples[0]['value']}")
            if field2_examples:
                print(f"     Example from {dup['file2']}: {field2_examples[0]['value']}")
            print()
    else:
        print("✓ No obvious duplicate field names found")
        print()
    
    # Analysis 2: Semantic grouping - fields that might be measuring the same thing
    print()
    print("ANALYSIS 2: SEMANTIC FIELD GROUPINGS")
    print("=" * 80)
    print("Fields grouped by common concepts that might need consolidation:")
    print()
    
    # Define semantic groups
    semantic_groups = {
        'Risk/Attitude': [],
        'Current Value/Amount': [],
        'Employee Contributions': [],
        'Employer Contributions': [],
        'Health/Medical': [],
        'Contact Information': [],
        'Mortgage/Loan Payments': [],
        'Savings/Cash': [],
        'Annual vs Monthly': [],
        'Retirement/Pension Strategy': [],
    }
    
    # Categorize fields
    all_unique_fields = only_in_file1 + only_in_file2
    
    for field in all_unique_fields:
        field_lower = field.lower()
        basename = get_field_basename(field).lower()
        source = file1_name if field in only_in_file1 else file2_name
        
        if 'risk' in basename or 'attitude' in basename:
            semantic_groups['Risk/Attitude'].append((field, source))
        
        if any(x in basename for x in ['current_value', 'current_fund_value', 'approx_current']):
            semantic_groups['Current Value/Amount'].append((field, source))
        
        if 'employee_contribution' in basename:
            semantic_groups['Employee Contributions'].append((field, source))
        
        if 'employer' in basename and ('match' in basename or 'contribution' in basename):
            semantic_groups['Employer Contributions'].append((field, source))
        
        if any(x in field_lower for x in ['health', 'smoker', 'medical', 'has_will']):
            semantic_groups['Health/Medical'].append((field, source))
        
        if any(x in basename for x in ['email', 'phone', 'mobile', 'contact']):
            semantic_groups['Contact Information'].append((field, source))
        
        if any(x in basename for x in ['mortgage_payment', 'monthly_payment', 'approx_monthly_payment']):
            semantic_groups['Mortgage/Loan Payments'].append((field, source))
        
        if any(x in field_lower for x in ['savings', 'cash', 'high_yield']):
            semantic_groups['Savings/Cash'].append((field, source))
        
        if ('annual' in basename or 'monthly' in basename) and 'amount' in basename:
            semantic_groups['Annual vs Monthly'].append((field, source))
        
        if any(x in field_lower for x in ['strategy', 'intended', 'plan', 'post_maturity']):
            semantic_groups['Retirement/Pension Strategy'].append((field, source))
    
    for group_name, fields in semantic_groups.items():
        if len(fields) > 1:
            print(f"📊 {group_name} ({len(fields)} fields)")
            for field, source in sorted(fields):
                print(f"  • [{source}] {field}")
                # Show example value
                if field in data['fields'] and data['fields'][field]['examples']:
                    example = data['fields'][field]['examples'][0]
                    value_preview = str(example['value'])[:60]
                    if len(str(example['value'])) > 60:
                        value_preview += "..."
                    print(f"      Example: {value_preview}")
            print()
    
    # Analysis 3: Nested structure differences
    print()
    print("ANALYSIS 3: STRUCTURAL COMPLEXITY DIFFERENCES")
    print("=" * 80)
    print()
    
    # Compare nesting depth
    def count_nesting(path: str) -> int:
        return path.count('[]') + path.count('.')
    
    file1_nesting = [count_nesting(f) for f in only_in_file1]
    file2_nesting = [count_nesting(f) for f in only_in_file2]
    
    print(f"Average nesting depth:")
    if file1_nesting:
        print(f"  {file1_name}: {sum(file1_nesting)/len(file1_nesting):.1f} levels")
    if file2_nesting:
        print(f"  {file2_name}: {sum(file2_nesting)/len(file2_nesting):.1f} levels")
    print()
    
    # Find deeply nested fields only in one file
    deeply_nested = []
    for field in only_in_file1:
        depth = count_nesting(field)
        if depth >= 5:
            deeply_nested.append((field, file1_name, depth))
    
    for field in only_in_file2:
        depth = count_nesting(field)
        if depth >= 5:
            deeply_nested.append((field, file2_name, depth))
    
    if deeply_nested:
        deeply_nested.sort(key=lambda x: x[2], reverse=True)
        print("Deeply nested fields (potential complexity issues):")
        for field, source, depth in deeply_nested:
            print(f"  • [{source}] Depth {depth}: {field}")
        print()
    
    # Analysis 4: Recommendations
    print()
    print("=" * 80)
    print("RECOMMENDATIONS FOR SCHEMA STABILITY")
    print("=" * 80)
    print()
    
    recommendations = []
    
    # Risk profile recommendation
    if any('risk_profile' in f for f in only_in_file1) and any('attitude_to_risk' in f for f in only_in_file2):
        recommendations.append({
            'priority': 'HIGH',
            'issue': 'Risk assessment field inconsistency',
            'description': 'risk_profile and attitude_to_risk represent the same concept',
            'suggestion': 'Consolidate into a single field: risk_profile (with standardized enum values)',
            'fields': [f for f in only_in_file1 if 'risk_profile' in f] + 
                     [f for f in only_in_file2 if 'attitude_to_risk' in f]
        })
    
    # Current value fields
    current_value_fields = [f for f in all_unique_fields if any(x in get_field_basename(f).lower() 
                           for x in ['current_value', 'current_fund_value', 'approx_current_value'])]
    if len(current_value_fields) > 1:
        recommendations.append({
            'priority': 'HIGH',
            'issue': 'Multiple current value field variants',
            'description': 'Different naming conventions for current values',
            'suggestion': 'Standardize to: current_fund_value (for all asset/pension values)',
            'fields': current_value_fields
        })
    
    # Annual vs Monthly inconsistency
    annual_fields = [f for f in all_unique_fields if 'annual' in get_field_basename(f).lower()]
    monthly_fields = [f for f in all_unique_fields if 'monthly' in get_field_basename(f).lower()]
    if annual_fields and monthly_fields:
        recommendations.append({
            'priority': 'MEDIUM',
            'issue': 'Inconsistent time period representation',
            'description': 'Some files use annual amounts, others use monthly',
            'suggestion': 'Support both annual_amount and monthly_amount fields, or standardize on one with a period indicator',
            'fields': annual_fields + monthly_fields
        })
    
    # Health details
    health_fields = [f for f in only_in_file2 if 'health_details' in f]
    if health_fields:
        recommendations.append({
            'priority': 'MEDIUM',
            'issue': 'Health details only captured in one file',
            'description': 'Health information not being extracted consistently',
            'suggestion': 'Make health_details fields optional but always present in schema',
            'fields': health_fields
        })
    
    # Contact information
    contact_fields = [f for f in only_in_file2 if any(x in get_field_basename(f).lower() 
                     for x in ['email', 'phone', 'mobile'])]
    if contact_fields:
        recommendations.append({
            'priority': 'MEDIUM',
            'issue': 'Contact information only in one file',
            'description': 'Contact details not consistently extracted',
            'suggestion': 'Ensure extraction prompt explicitly asks for contact information',
            'fields': contact_fields
        })
    
    # Deeply nested pension structure
    pension_timeline_timeline = [f for f in all_unique_fields if 'timeline[].timeline[]' in f]
    if pension_timeline_timeline:
        recommendations.append({
            'priority': 'LOW',
            'issue': 'Complex nested timeline structure',
            'description': 'pensions[].timeline[].timeline[] creates unnecessary complexity',
            'suggestion': 'Consider flattening to pensions[].timeline[] or using named sub-objects',
            'fields': pension_timeline_timeline
        })
    
    # Display recommendations
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. [{rec['priority']}] {rec['issue']}")
        print(f"   Issue: {rec['description']}")
        print(f"   Suggestion: {rec['suggestion']}")
        print(f"   Affected fields ({len(rec['fields'])}):")
        for field in rec['fields'][:5]:  # Show first 5
            print(f"     • {field}")
        if len(rec['fields']) > 5:
            print(f"     ... and {len(rec['fields']) - 5} more")
        print()
    
    # Summary statistics
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total unique fields: {len(all_unique_fields)}")
    print(f"Fields only in {file1_name}: {len(only_in_file1)}")
    print(f"Fields only in {file2_name}: {len(only_in_file2)}")
    print(f"Fields in both: {len(fields_in_both)}")
    print(f"Overlap percentage: {len(fields_in_both) / len(data['fields']) * 100:.1f}%")
    print()
    print(f"High priority recommendations: {sum(1 for r in recommendations if r['priority'] == 'HIGH')}")
    print(f"Medium priority recommendations: {sum(1 for r in recommendations if r['priority'] == 'MEDIUM')}")
    print(f"Low priority recommendations: {sum(1 for r in recommendations if r['priority'] == 'LOW')}")
    print()


if __name__ == '__main__':
    analyze_schema_stability('/home/igor/test_task/combined_schema_examples_2.json')
