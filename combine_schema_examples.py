#!/usr/bin/env python3
"""
Script to combine schema structure with real examples from structured result files.

For each field in the schema, extracts:
- Path in the schema
- Enum values (if applicable)
- Real example values from structured_result.json
- Real example values from structured_result_2.json
- Example citations from both files
"""

import json
from typing import Any, Dict, List, Set, Tuple
from collections import defaultdict


class SchemaExampleCombiner:
    def __init__(self):
        self.combined_data = {}
        self.schema = None
        self.examples = []
        
    def load_files(self, schema_path: str, example_paths: List[str]):
        """Load schema and example files"""
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)
        
        for path in example_paths:
            with open(path, 'r') as f:
                self.examples.append({
                    'path': path,
                    'data': json.load(f)
                })
    
    def extract_enum_values(self, schema_node: Any, path: str = "") -> Dict[str, List[str]]:
        """Recursively extract enum values from schema"""
        enums = {}
        
        if isinstance(schema_node, dict):
            # Check if this node has an enum
            if 'enum' in schema_node:
                enums[path] = schema_node['enum']
            
            # Check in properties
            if 'properties' in schema_node:
                for prop_name, prop_value in schema_node['properties'].items():
                    new_path = f"{path}.{prop_name}" if path else prop_name
                    enums.update(self.extract_enum_values(prop_value, new_path))
            
            # Check in allOf (commonly used for constraints)
            if 'allOf' in schema_node:
                for item in schema_node['allOf']:
                    enums.update(self.extract_enum_values(item, path))
            
            # Check in oneOf
            if 'oneOf' in schema_node:
                for item in schema_node['oneOf']:
                    enums.update(self.extract_enum_values(item, path))
            
            # Check in items (for arrays)
            if 'items' in schema_node:
                enums.update(self.extract_enum_values(schema_node['items'], path + "[]"))
            
            # Check in definitions
            if 'definitions' in schema_node:
                for def_name, def_value in schema_node['definitions'].items():
                    enums.update(self.extract_enum_values(def_value, f"#/definitions/{def_name}"))
            
            # Check in $ref (resolve references)
            if '$ref' in schema_node:
                ref_path = schema_node['$ref']
                # We'll handle this by noting the reference
                pass
        
        return enums
    
    def extract_values_from_data(self, data: Any, path: str = "", current_full_path: str = "") -> Dict[str, List[Dict]]:
        """
        Recursively extract values and citations from example data.
        Returns dict mapping path to list of {value, citation, type, full_path}
        """
        values = defaultdict(list)
        
        if isinstance(data, dict):
            # Check if this is a ScalarFact (has type, value, citation)
            if 'type' in data and 'value' in data and 'citation' in data:
                # Store the value at the current path (for the ScalarFact as a whole)
                values[current_full_path].append({
                    'value': data['value'],
                    'citation': data['citation'],
                    'type': data.get('type'),
                    'call_time': data.get('call_time', 'N/A')
                })
                # ALSO create explicit entries for nested paths .value, .type, .citation
                # This ensures schema paths like "asset_type.value" get matched
                if current_full_path:
                    # Store the value field with full context
                    values[f"{current_full_path}.value"].append({
                        'value': data['value'],
                        'citation': data['citation'],
                        'type': data.get('type'),
                        'call_time': data.get('call_time', 'N/A')
                    })
                    # Store the type field
                    values[f"{current_full_path}.type"].append({
                        'value': data['type'],
                        'citation': data['citation'],
                        'type': 'string',
                        'call_time': data.get('call_time', 'N/A')
                    })
                    # Store the citation field
                    values[f"{current_full_path}.citation"].append({
                        'value': data['citation'],
                        'citation': data['citation'],
                        'type': 'string',
                        'call_time': data.get('call_time', 'N/A')
                    })
            else:
                # Recurse into object properties
                for key, value in data.items():
                    new_path = f"{current_full_path}.{key}" if current_full_path else key
                    nested_values = self.extract_values_from_data(value, path, new_path)
                    # Manually merge: extend lists instead of replacing
                    for nested_path, nested_list in nested_values.items():
                        values[nested_path].extend(nested_list)
        
        elif isinstance(data, list):
            # Handle arrays
            for idx, item in enumerate(data):
                # For arrays, we use [] notation without index for schema matching
                new_path = f"{current_full_path}[]"
                nested_values = self.extract_values_from_data(item, path, new_path)
                # Manually merge: extend lists instead of replacing
                for nested_path, nested_list in nested_values.items():
                    values[nested_path].extend(nested_list)
        
        return values
    
    def normalize_path(self, path: str) -> str:
        """Normalize paths for matching (handle array indices, etc.)"""
        # Remove array indices like [0], [1] and replace with []
        import re
        normalized = re.sub(r'\[\d+\]', '[]', path)
        return normalized
    
    def map_data_path_to_schema_path(self, data_path: str) -> List[str]:
        """
        Map a data path to potential schema definition paths.
        E.g., 'assets[].static.asset_type.value' -> ['#/definitions/AssetItem.static.asset_type.value']
        """
        # Common mappings from data array names to schema definitions
        mappings = {
            'assets[]': '#/definitions/AssetItem',
            'clients[]': '#/definitions/Client',
            'loans_and_mortgages[]': '#/definitions/LoanOrMortgage',
            'income_sources[]': '#/definitions/IncomeSource',
            'expenses[]': '#/definitions/Expense',
            'goals[]': '#/definitions/Goal',
        }
        
        potential_paths = [data_path]  # Always include the original path
        
        # Try to map array prefixes to definitions
        for data_prefix, schema_prefix in mappings.items():
            if data_path.startswith(data_prefix):
                # Replace the data prefix with schema prefix
                remainder = data_path[len(data_prefix):]
                if remainder.startswith('.'):
                    remainder = remainder[1:]
                schema_path = f"{schema_prefix}.{remainder}" if remainder else schema_prefix
                potential_paths.append(schema_path)
        
        return potential_paths
    
    def combine_data(self):
        """Main method to combine schema and examples"""
        result = {
            'schema_file': 'schema2.json',
            'example_files': [ex['path'] for ex in self.examples],
            'fields': {}
        }
        
        # Extract enum values from schema
        print("Extracting enum values from schema...")
        enum_values = self.extract_enum_values(self.schema)
        
        # Extract values from all example files
        print("Extracting values from example files...")
        all_example_values = []
        for example in self.examples:
            example_values = self.extract_values_from_data(example['data'])
            all_example_values.append({
                'source': example['path'],
                'values': example_values
            })
        
        # Collect all unique paths
        all_paths = set()
        
        # Add paths from enums
        all_paths.update(enum_values.keys())
        
        # Add paths from examples
        for ex_values in all_example_values:
            all_paths.update(ex_values['values'].keys())
        
        print(f"Found {len(all_paths)} unique paths")
        
        # Combine data for each path
        for path in sorted(all_paths):
            field_data = {
                'path': path,
                'enum_values': [],
                'examples': []
            }
            
            # Collect enum values (use a set to avoid duplicates)
            enum_set = set()
            
            # Add enum values if present
            if path in enum_values:
                enum_set.update(enum_values[path])
            
            # Check for enum in definition references
            for enum_path, enum_list in enum_values.items():
                if '#/definitions/' in enum_path:
                    # Try to match based on property name
                    def_name = enum_path.split('/')[-1]
                    if path.endswith(def_name) or f".{def_name}" in path:
                        enum_set.update(enum_list)
            
            # Convert set back to list (preserve order if possible)
            field_data['enum_values'] = list(enum_set)
            
            # Add examples from all sources
            # Collect examples from all matching paths
            for ex_values in all_example_values:
                # Build list of paths to check for this current path
                paths_to_check = [path]
                
                # If this is a schema definition path, find corresponding data paths
                if '#/definitions/' in path:
                    # Map from schema to data paths (reverse mapping)
                    # Check all data paths to see if they map to this schema path
                    for data_path in ex_values['values'].keys():
                        mapped_paths = self.map_data_path_to_schema_path(data_path)
                        if path in mapped_paths:
                            paths_to_check.append(data_path)
                # If this is a data path, also check for mapped schema paths
                else:
                    mapped_paths = self.map_data_path_to_schema_path(path)
                    paths_to_check.extend(mapped_paths)
                
                # Look for examples in all candidate paths
                for check_path in paths_to_check:
                    if check_path in ex_values['values']:
                        for example in ex_values['values'][check_path]:
                            # Avoid duplicates
                            example_data = {
                                'source': ex_values['source'],
                                'value': example['value'],
                                'citation': example['citation'],
                                'type': example['type'],
                                'call_time': example.get('call_time', 'N/A')
                            }
                            if example_data not in field_data['examples']:
                                field_data['examples'].append(example_data)
            
            # Only add if we have enum values or examples
            if field_data['enum_values'] or field_data['examples']:
                result['fields'][path] = field_data
        
        return result
    
    def save_combined_data(self, output_path: str, combined_data: Dict):
        """Save combined data to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
        print(f"Combined data saved to {output_path}")
    
    def generate_summary_report(self, combined_data: Dict) -> str:
        """Generate a human-readable summary report"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("SCHEMA + EXAMPLES COMBINATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append(f"Schema file: {combined_data['schema_file']}")
        report_lines.append(f"Example files: {', '.join(combined_data['example_files'])}")
        report_lines.append(f"Total fields analyzed: {len(combined_data['fields'])}")
        report_lines.append("")
        
        # Add per-file statistics
        file1_path = combined_data['example_files'][0]
        file2_path = combined_data['example_files'][1]
        file1_name = file1_path.split('/')[-1]
        file2_name = file2_path.split('/')[-1]
        
        fields_in_file1 = set()
        fields_in_file2 = set()
        fields_in_both = set()
        
        for path, field_data in combined_data['fields'].items():
            has_file1 = any(file1_path in ex['source'] for ex in field_data['examples'])
            has_file2 = any(file2_path in ex['source'] for ex in field_data['examples'])
            
            if has_file1:
                fields_in_file1.add(path)
            if has_file2:
                fields_in_file2.add(path)
            if has_file1 and has_file2:
                fields_in_both.add(path)
        
        examples_in_file1 = sum(
            sum(1 for ex in f['examples'] if file1_path in ex['source'])
            for f in combined_data['fields'].values()
        )
        examples_in_file2 = sum(
            sum(1 for ex in f['examples'] if file2_path in ex['source'])
            for f in combined_data['fields'].values()
        )
        
        report_lines.append("COVERAGE BY FILE:")
        report_lines.append("-" * 80)
        report_lines.append(f"{file1_name}: {len(fields_in_file1)} fields filled, {examples_in_file1} examples")
        report_lines.append(f"{file2_name}: {len(fields_in_file2)} fields filled, {examples_in_file2} examples")
        report_lines.append(f"Fields with examples in BOTH files: {len(fields_in_both)}")
        report_lines.append(f"Fields ONLY in {file1_name}: {len(fields_in_file1 - fields_in_file2)}")
        report_lines.append(f"Fields ONLY in {file2_name}: {len(fields_in_file2 - fields_in_file1)}")
        report_lines.append("")
        
        # List fields only in file 1
        only_in_file1 = sorted(fields_in_file1 - fields_in_file2)
        if only_in_file1:
            report_lines.append(f"FIELDS ONLY IN {file1_name}:")
            report_lines.append("-" * 80)
            for field_path in only_in_file1:
                report_lines.append(f"  • {field_path}")
            report_lines.append("")
        
        # List fields only in file 2
        only_in_file2 = sorted(fields_in_file2 - fields_in_file1)
        if only_in_file2:
            report_lines.append(f"FIELDS ONLY IN {file2_name}:")
            report_lines.append("-" * 80)
            for field_path in only_in_file2:
                report_lines.append(f"  • {field_path}")
            report_lines.append("")
        
        # List fields in both
        fields_in_both_sorted = sorted(fields_in_both)
        if fields_in_both_sorted:
            report_lines.append(f"FIELDS IN BOTH FILES:")
            report_lines.append("-" * 80)
            for field_path in fields_in_both_sorted:
                report_lines.append(f"  • {field_path}")
            report_lines.append("")
        
        report_lines.append("=" * 80)
        report_lines.append("")
        
        for path, field_data in sorted(combined_data['fields'].items()):
            report_lines.append(f"PATH: {path}")
            report_lines.append("-" * 80)
            
            if field_data['enum_values']:
                report_lines.append(f"  ENUM VALUES ({len(field_data['enum_values'])}):")
                for enum_val in field_data['enum_values']:
                    report_lines.append(f"    - {enum_val}")
                report_lines.append("")
            
            if field_data['examples']:
                report_lines.append(f"  EXAMPLES ({len(field_data['examples'])}):")
                for idx, example in enumerate(field_data['examples'][:5], 1):  # Limit to 5 examples
                    report_lines.append(f"    [{idx}] From: {example['source'].split('/')[-1]}")
                    report_lines.append(f"        Value: {example['value']}")
                    report_lines.append(f"        Type: {example['type']}")
                    report_lines.append(f"        Call time: {example['call_time']}")
                    citation_preview = example['citation'][:100] + "..." if len(example['citation']) > 100 else example['citation']
                    report_lines.append(f"        Citation: {citation_preview}")
                    report_lines.append("")
                
                if len(field_data['examples']) > 5:
                    report_lines.append(f"    ... and {len(field_data['examples']) - 5} more examples")
                    report_lines.append("")
            
            report_lines.append("")
        
        return "\n".join(report_lines)


def main():
    print("Schema + Examples Combiner")
    print("=" * 80)
    
    combiner = SchemaExampleCombiner()
    
    # Load files
    schema_path = '/home/igor/test_task/start/schema2.json'
    example_paths = [
        '/home/igor/test_task/best/res1.json',
        '/home/igor/test_task/best/res2.json'
    ]
    
    print(f"Loading schema: {schema_path}")
    print(f"Loading examples: {example_paths}")
    print()
    
    combiner.load_files(schema_path, example_paths)
    
    # Combine data
    print("Combining data...")
    combined_data = combiner.combine_data()
    
    # Save combined JSON
    output_json = '/home/igor/test_task/combined_schema_examples_2.json'
    combiner.save_combined_data(output_json, combined_data)
    
    # Generate and save report
    print("Generating summary report...")
    report = combiner.generate_summary_report(combined_data)
    output_report = '/home/igor/test_task/combined_schema_examples_report.txt'
    with open(output_report, 'w') as f:
        f.write(report)
    print(f"Summary report saved to {output_report}")
    
    # Print some statistics
    print()
    print("=" * 80)
    print("STATISTICS")
    print("=" * 80)
    print(f"Total fields: {len(combined_data['fields'])}")
    
    fields_with_enums = sum(1 for f in combined_data['fields'].values() if f['enum_values'])
    fields_with_examples = sum(1 for f in combined_data['fields'].values() if f['examples'])
    
    print(f"Fields with enum values: {fields_with_enums}")
    print(f"Fields with examples: {fields_with_examples}")
    
    total_examples = sum(len(f['examples']) for f in combined_data['fields'].values())
    print(f"Total examples collected: {total_examples}")
    
    # Per-file statistics
    print()
    print("Coverage by file:")
    print("-" * 80)
    
    file1_name = example_paths[0].split('/')[-1]
    file2_name = example_paths[1].split('/')[-1]
    
    fields_in_file1 = set()
    fields_in_file2 = set()
    fields_in_both = set()
    
    for path, field_data in combined_data['fields'].items():
        has_file1 = False
        has_file2 = False
        
        for example in field_data['examples']:
            if example_paths[0] in example['source']:
                has_file1 = True
                fields_in_file1.add(path)
            if example_paths[1] in example['source']:
                has_file2 = True
                fields_in_file2.add(path)
        
        if has_file1 and has_file2:
            fields_in_both.add(path)
    
    print(f"{file1_name}: {len(fields_in_file1)} fields filled")
    print(f"{file2_name}: {len(fields_in_file2)} fields filled")
    print(f"Fields with examples in BOTH files: {len(fields_in_both)}")
    print(f"Fields ONLY in {file1_name}: {len(fields_in_file1 - fields_in_file2)}")
    print(f"Fields ONLY in {file2_name}: {len(fields_in_file2 - fields_in_file1)}")
    
    # Count examples per file
    examples_in_file1 = sum(
        sum(1 for ex in f['examples'] if example_paths[0] in ex['source'])
        for f in combined_data['fields'].values()
    )
    examples_in_file2 = sum(
        sum(1 for ex in f['examples'] if example_paths[1] in ex['source'])
        for f in combined_data['fields'].values()
    )
    
    print()
    print("Total examples by file:")
    print(f"{file1_name}: {examples_in_file1} examples")
    print(f"{file2_name}: {examples_in_file2} examples")
    
    print()
    print("Done!")


if __name__ == '__main__':
    main()

