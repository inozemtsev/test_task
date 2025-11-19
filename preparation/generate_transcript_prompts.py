#!/usr/bin/env python3
"""
Script to generate prompts for creating realistic financial transcript chunks.

For each high-level part (assets, pensions, clients, etc.):
1. Generate diverse client cases
2. Create prompts with:
   - General instruction
   - Client case description
   - Attribute values from examples
   - Citations as few-shot examples
   - Citations organized by call_time
"""

import json
import random
from typing import Dict, List, Any
from collections import defaultdict


class TranscriptPromptGenerator:
    def __init__(self):
        self.combined_data = None
        self.res_data = []
        self.client_personas = []
        self.persona_name_pool = {
            'male': ['James', 'Michael', 'Robert', 'David', 'John', 'William', 
                    'Richard', 'Thomas', 'Charles', 'Daniel', 'Paul', 'Mark',
                    'George', 'Steven', 'Andrew', 'Edward', 'Brian', 'Kevin'],
            'female': ['Mary', 'Patricia', 'Jennifer', 'Linda', 'Barbara', 'Elizabeth',
                      'Susan', 'Jessica', 'Sarah', 'Karen', 'Nancy', 'Margaret',
                      'Lisa', 'Betty', 'Dorothy', 'Sandra', 'Ashley', 'Emily'],
            'surnames': ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia',
                        'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Wilson', 'Anderson',
                        'Taylor', 'Thomas', 'Moore', 'Jackson', 'Martin', 'Lee',
                        'Thompson', 'White', 'Harris', 'Clark', 'Lewis', 'Robinson']
        }
        
    def load_data(self, combined_path: str, res_paths: List[str]):
        """Load combined schema examples and result files"""
        with open(combined_path, 'r') as f:
            self.combined_data = json.load(f)
        
        for path in res_paths:
            with open(path, 'r') as f:
                self.res_data.append({
                    'path': path,
                    'data': json.load(f)
                })
    
    def generate_client_personas(self, instances_per_type: int = 2) -> List[Dict]:
        """Generate diverse client personas/cases with multiple instances per type"""
        
        # Define persona type templates
        persona_types = [
            {
                'type_id': 'young_couple',
                'type_name': 'Young Professional Couple',
                'base_description': 'A married couple in their early 30s, both employed full-time, with young children. They own their first home with a mortgage, have some savings, and are starting to think about retirement planning.',
                'age_range': (30, 35),
                'marital_status': 'married',
                'employment': 'both employed',
                'life_stage': 'young family',
                'variations': [
                    'They have two young children and recently bought their first home',
                    'They have one toddler and are expecting their second child',
                    'They have three children under 10 and managing childcare costs',
                ]
            },
            {
                'type_id': 'single_professional',
                'type_name': 'Single Young Professional',
                'base_description': 'A single individual in their late 20s to early 30s, focused on career growth. They are renting or recently bought their first property, have some savings and investments, and are building their financial foundation.',
                'age_range': (27, 34),
                'marital_status': 'single',
                'employment': 'employed',
                'life_stage': 'career building',
                'variations': [
                    'They recently got promoted and want to optimize their finances',
                    'They are saving for their first home deposit while paying off student loans',
                    'They have a high salary but limited financial knowledge',
                ]
            },
            {
                'type_id': 'cohabiting_couple',
                'type_name': 'Cohabiting Couple',
                'base_description': 'An unmarried couple living together in their 30s. They are both employed, may have children, and need advice on financial planning without being married, including property ownership and protection.',
                'age_range': (30, 40),
                'marital_status': 'cohabiting',
                'employment': 'both employed',
                'life_stage': 'committed relationship',
                'variations': [
                    'They have been together for 5+ years and own property jointly',
                    'They have children together and want to ensure financial protection',
                    'They are planning to marry in the future but need interim planning',
                ]
            },
            {
                'type_id': 'mid_career',
                'type_name': 'Mid-Career Couple',
                'base_description': 'A couple in their early to mid-40s with teenage children. Both are established in their careers with good income, manageable mortgage, growing savings, and thinking seriously about retirement planning.',
                'age_range': (40, 48),
                'marital_status': 'married',
                'employment': 'both employed',
                'life_stage': 'established family',
                'variations': [
                    'They are balancing saving for retirement with university costs for children',
                    'They recently refinanced their mortgage and have increased savings capacity',
                    'One is considering a career change while the other is stable',
                ]
            },
            {
                'type_id': 'pre_retirement',
                'type_name': 'Pre-Retirement Couple',
                'base_description': 'A couple in their late 50s approaching retirement. Both have been employed for decades, own multiple properties, have substantial pensions, and are planning their retirement income strategy.',
                'age_range': (55, 60),
                'marital_status': 'married',
                'employment': 'employed, planning retirement',
                'life_stage': 'pre-retirement',
                'variations': [
                    'They plan to retire in 3-5 years and want to maximize pension contributions',
                    'One is already semi-retired while the other still works full-time',
                    'They own rental properties and are considering downsizing',
                ]
            },
            {
                'type_id': 'early_retiree',
                'type_name': 'Early Retirement Seeker',
                'base_description': 'A couple or individual in their early 50s who want to retire before traditional retirement age. They have substantial savings and investments, minimal debt, and need advice on making their money last.',
                'age_range': (50, 56),
                'marital_status': 'married',
                'employment': 'employed, planning early retirement',
                'life_stage': 'early retirement planning',
                'variations': [
                    'They have saved aggressively and want to retire at 55',
                    'They plan to semi-retire and do consulting work',
                    'They want to retire early to travel while still healthy',
                ]
            },
            {
                'type_id': 'recently_retired',
                'type_name': 'Recently Retired Couple',
                'base_description': 'A couple in their mid-60s who have recently retired. They have pension income, investment portfolios, own their home outright, and are focused on estate planning and maintaining their lifestyle.',
                'age_range': (63, 67),
                'marital_status': 'married',
                'employment': 'retired',
                'life_stage': 'retired',
                'variations': [
                    'They retired last year and are adjusting to living on pension income',
                    'They have been retired for 2 years and considering part-time work',
                    'They recently paid off their mortgage and focusing on travel',
                ]
            },
            {
                'type_id': 'empty_nesters',
                'type_name': 'Empty Nest Couple',
                'base_description': 'A couple in their late 50s whose children have left home. They both work, have paid off or nearly paid off their mortgage, and are reassessing their financial priorities now that children are independent.',
                'age_range': (55, 62),
                'marital_status': 'married',
                'employment': 'both employed',
                'life_stage': 'empty nest',
                'variations': [
                    'Their last child just went to university and they have reduced expenses',
                    'They are considering downsizing their family home',
                    'They want to accelerate retirement savings now children are independent',
                ]
            },
            {
                'type_id': 'self_employed',
                'type_name': 'Self-Employed Business Owner',
                'base_description': 'A self-employed individual in their 40s who owns a small business. They have irregular income, business assets, personal investments, and need advice on tax efficiency and retirement planning.',
                'age_range': (40, 50),
                'marital_status': 'married',
                'employment': 'self-employed',
                'life_stage': 'mid-career',
                'variations': [
                    'They run a consulting business and have variable monthly income',
                    'They own a retail business and are considering expansion',
                    'They are a freelance professional with multiple revenue streams',
                ]
            },
            {
                'type_id': 'blended_family',
                'type_name': 'Blended Family',
                'base_description': 'A remarried couple in their 40s with children from previous relationships. They have complex financial situations including maintenance payments, multiple properties, and need advice on integrating finances.',
                'age_range': (40, 50),
                'marital_status': 'married',
                'employment': 'both employed',
                'life_stage': 'blended family',
                'variations': [
                    'They both have children from previous marriages living with them part-time',
                    'They are managing maintenance payments and saving for their shared future',
                    'They need estate planning that considers all children fairly',
                ]
            },
            {
                'type_id': 'career_changer',
                'type_name': 'Career Transition Individual',
                'base_description': 'An individual in their late 30s to 40s going through a career change or returning to work. They may have gaps in pension contributions, are rebuilding savings, and need advice on getting back on track.',
                'age_range': (38, 48),
                'marital_status': 'married',
                'employment': 'changing career',
                'life_stage': 'career transition',
                'variations': [
                    'They took time off to raise children and are now returning to work',
                    'They are retraining for a completely different career',
                    'They left corporate work to start their own business',
                ]
            },
            {
                'type_id': 'divorced_single',
                'type_name': 'Divorced Single Parent',
                'base_description': 'A divorced individual in their 40s with dependent children. They are employed, recently went through divorce settlement, have some assets and pension, and need to rebuild their financial plan.',
                'age_range': (40, 48),
                'marital_status': 'divorced',
                'employment': 'employed',
                'life_stage': 'single parent',
                'variations': [
                    'They have two teenagers and share custody with their ex-spouse',
                    'They have primary custody of three children and receive maintenance',
                    'Their divorce was finalized last year and rebuilding savings',
                ]
            },
            {
                'type_id': 'inheritance_recipient',
                'type_name': 'Recent Inheritance Recipient',
                'base_description': 'An individual or couple in their 30s-50s who recently received a significant inheritance. They are employed, may have existing mortgages and investments, and need advice on managing this windfall wisely.',
                'age_range': (35, 55),
                'marital_status': 'married',
                'employment': 'employed',
                'life_stage': 'windfall management',
                'variations': [
                    'They inherited from parents and want to invest it for their children',
                    'They received a large inheritance and considering paying off their mortgage',
                    'They want to use inheritance to retire early',
                ]
            },
            {
                'type_id': 'high_earner',
                'type_name': 'High-Earning Professionals',
                'base_description': 'A couple in their late 40s, both in high-paying professional careers. They have substantial income, multiple properties, significant investments, complex tax situations, and inheritance planning needs.',
                'age_range': (45, 52),
                'marital_status': 'married',
                'employment': 'both employed (high income)',
                'life_stage': 'wealth accumulation',
                'variations': [
                    'They are both senior executives with stock options and bonuses',
                    'One is a doctor and the other is a lawyer with substantial debt from education',
                    'They have built a significant property portfolio and investment accounts',
                ]
            },
            {
                'type_id': 'semi_retired',
                'type_name': 'Semi-Retired Professional',
                'base_description': 'An individual in their early 60s who has partially retired but still works part-time or freelance. They have pension income starting, some employment income, investments, and are transitioning gradually to full retirement.',
                'age_range': (60, 68),
                'marital_status': 'married',
                'employment': 'semi-retired',
                'life_stage': 'gradual retirement',
                'variations': [
                    'They reduced hours to 3 days per week and drawing some pension',
                    'They do freelance consulting to supplement pension income',
                    'They plan to fully retire in 2-3 years',
                ]
            },
            {
                'type_id': 'widowed',
                'type_name': 'Widowed Individual',
                'base_description': 'A widowed individual in their 70s with adult children. They receive pension income, have inherited assets, own their home, and need advice on estate planning and managing inherited wealth.',
                'age_range': (70, 75),
                'marital_status': 'widowed',
                'employment': 'retired',
                'life_stage': 'late retirement',
                'variations': [
                    'Their spouse passed away 2 years ago and they inherited substantial assets',
                    'They live alone and receive multiple pension incomes',
                    'They are considering moving closer to their children',
                ]
            },
            {
                'type_id': 'first_time_buyer',
                'type_name': 'First-Time Homebuyer',
                'base_description': 'A couple or individual in their late 20s to mid-30s preparing to buy their first home. They are saving for a deposit, both employed, and need advice on mortgages, protection, and managing finances as homeowners.',
                'age_range': (28, 36),
                'marital_status': 'married',
                'employment': 'both employed',
                'life_stage': 'first home purchase',
                'variations': [
                    'They have saved a 15% deposit and are ready to buy',
                    'They are using Help to Buy or first-time buyer schemes',
                    'They are choosing between buying now or saving a larger deposit',
                ]
            }
        ]
        
        personas = []
        used_names = set()
        used_ids = set()
        
        for persona_type in persona_types:
            for i in range(instances_per_type):
                max_attempts = 100
                attempts = 0
                persona_id = None
                
                # Generate unique names with persona ID uniqueness check
                while attempts < max_attempts:
                    if persona_type['marital_status'] in ['married', 'civil_partnership']:
                        # Generate couple names
                        male_first = random.choice(self.persona_name_pool['male'])
                        female_first = random.choice(self.persona_name_pool['female'])
                        surname = random.choice(self.persona_name_pool['surnames'])
                        
                        name_key = f"{male_first}_{female_first}_{surname}_{i}"
                        # Include instance number in persona_id to ensure uniqueness
                        persona_id = f"{persona_type['type_id']}_{i+1:02d}_{male_first.lower()}_{female_first.lower()}"
                        client_names = f"{male_first} and {female_first} {surname}"
                    else:
                        # Generate single person name
                        gender = random.choice(['male', 'female'])
                        first_name = random.choice(self.persona_name_pool[gender])
                        surname = random.choice(self.persona_name_pool['surnames'])
                        
                        name_key = f"{first_name}_{surname}_{i}"
                        # Include instance number in persona_id to ensure uniqueness
                        persona_id = f"{persona_type['type_id']}_{i+1:02d}_{first_name.lower()}"
                        client_names = f"{first_name} {surname}"
                    
                    # Check if both name_key and persona_id are unique
                    if name_key not in used_names and persona_id not in used_ids:
                        used_names.add(name_key)
                        used_ids.add(persona_id)
                        break
                    
                    attempts += 1
                
                # If we couldn't generate unique names, add fallback
                if attempts >= max_attempts:
                    if persona_type['marital_status'] in ['married', 'civil_partnership']:
                        persona_id = f"{persona_type['type_id']}_{i+1:02d}_couple"
                        client_names = f"Client Couple {i+1}"
                    else:
                        persona_id = f"{persona_type['type_id']}_{i+1:02d}_person"
                        client_names = f"Client {i+1}"
                    used_ids.add(persona_id)
                
                # Pick a variation
                variation = random.choice(persona_type['variations'])
                
                # Generate specific age within range
                age_min, age_max = persona_type['age_range']
                if persona_type['marital_status'] in ['married', 'civil_partnership']:
                    age1 = random.randint(age_min, age_max)
                    age2 = random.randint(age_min, age_max)
                    age_display = f"{age1} and {age2}"
                else:
                    age = random.randint(age_min, age_max)
                    age_display = str(age)
                
                # Create persona instance
                persona = {
                    'id': persona_id,
                    'type': persona_type['type_id'],
                    'name': f"{persona_type['type_name']}: {client_names}",
                    'client_names': client_names,
                    'description': f"{persona_type['base_description']} {variation}",
                    'age': age_display,
                    'age_range': f"{age_min}-{age_max}",
                    'marital_status': persona_type['marital_status'],
                    'employment': persona_type['employment'],
                    'life_stage': persona_type['life_stage'],
                    'variation': variation
                }
                
                personas.append(persona)
        
        return personas
    
    def extract_high_level_parts(self) -> Dict[str, List[str]]:
        """Extract high-level parts from the combined data"""
        parts = defaultdict(list)
        
        for path in self.combined_data['fields'].keys():
            # Extract top-level category
            if '[]' in path:
                category = path.split('[]')[0] + '[]'
            elif path.startswith('#/definitions/'):
                continue  # Skip definitions for now
            else:
                category = path.split('.')[0] if '.' in path else path
            
            parts[category].append(path)
        
        return dict(parts)
    
    def get_examples_for_part(self, part_prefix: str) -> Dict[str, Any]:
        """Get all examples for a specific high-level part"""
        examples = {}
        
        for path, field_data in self.combined_data['fields'].items():
            if path.startswith(part_prefix):
                if field_data['examples']:
                    examples[path] = {
                        'enum_values': field_data.get('enum_values', []),
                        'examples': field_data['examples']
                    }
        
        return examples
    
    def extract_citations_by_time(self, examples: Dict[str, Any]) -> List[Dict]:
        """Extract and organize citations by call_time"""
        citations_with_time = []
        
        for path, data in examples.items():
            for example in data['examples']:
                if example.get('call_time') and example['call_time'] != 'N/A':
                    citations_with_time.append({
                        'call_time': example['call_time'],
                        'path': path,
                        'value': example['value'],
                        'citation': example['citation'],
                        'type': example['type']
                    })
        
        # Sort by call_time
        citations_with_time.sort(key=lambda x: self.parse_time(x['call_time']))
        
        return citations_with_time
    
    def parse_time(self, time_str: str) -> int:
        """Parse time string like '00:05:55' to seconds"""
        try:
            parts = time_str.strip().split(':')
            if len(parts) == 3:
                h, m, s = map(int, parts)
                return h * 3600 + m * 60 + s
            elif len(parts) == 2:
                m, s = map(int, parts)
                return m * 60 + s
        except:
            return 0
        return 0
    
    def format_attribute_examples(self, examples: Dict[str, Any], max_per_field: int = 3) -> str:
        """Format attribute examples for the prompt"""
        lines = []
        
        for path, data in sorted(examples.items()):
            # Clean up path for display
            display_path = path.replace('[]', '').replace('.', ' > ')
            
            lines.append(f"\n### {display_path}")
            
            # Show enum values if available
            if data['enum_values']:
                lines.append(f"**Allowed values:** {', '.join(data['enum_values'])}")
            
            # Show examples
            if data['examples']:
                lines.append(f"**Example values:**")
                for i, ex in enumerate(data['examples'][:max_per_field], 1):
                    lines.append(f"  {i}. `{ex['value']}`")
                    if ex['citation'] and ex['citation'] != 'N/A':
                        citation_preview = ex['citation'][:100] + '...' if len(ex['citation']) > 100 else ex['citation']
                        lines.append(f"     Citation: \"{citation_preview}\"")
        
        return '\n'.join(lines)
    
    def format_citation_examples(self, citations: List[Dict], max_count: int = 10) -> str:
        """Format citations as few-shot examples"""
        lines = []
        lines.append("\n## Few-Shot Citation Examples")
        lines.append("\nBelow are examples of how to format citations with timestamps:\n")
        
        for i, cit in enumerate(citations[:max_count], 1):
            field_name = cit['path'].split('.')[-1] if '.' in cit['path'] else cit['path']
            lines.append(f"{i}. **[{cit['call_time']}]** {field_name}: `{cit['value']}`")
            lines.append(f"   > {cit['citation']}")
            lines.append("")
        
        return '\n'.join(lines)
    
    def generate_prompt_for_part(self, part_name: str, persona: Dict) -> str:
        """Generate a complete prompt for a specific high-level part"""
        
        # Get examples for this part
        examples = self.get_examples_for_part(part_name)
        
        if not examples:
            return None
        
        # Extract citations by time
        citations_by_time = self.extract_citations_by_time(examples)
        
        # Generate the prompt
        prompt_lines = []
        
        # 1. General instruction
        prompt_lines.append("# Financial Fact-Find Transcript Generation Task")
        prompt_lines.append("")
        prompt_lines.append("You are generating a realistic segment of a financial advisor's fact-find conversation with a client.")
        prompt_lines.append("The conversation should be natural, professional, and include specific factual information with proper timestamp citations.")
        prompt_lines.append("")
        
        # 2. Client case description
        prompt_lines.append(f"## Client Case: {persona['name']}")
        prompt_lines.append("")
        prompt_lines.append(f"**Client Names:** {persona['client_names']}")
        prompt_lines.append("")
        prompt_lines.append(f"**Description:** {persona['description']}")
        prompt_lines.append("")
        prompt_lines.append(f"**Profile:**")
        prompt_lines.append(f"- Age: {persona['age']}")
        prompt_lines.append(f"- Marital status: {persona['marital_status']}")
        prompt_lines.append(f"- Employment: {persona['employment']}")
        prompt_lines.append(f"- Life stage: {persona['life_stage']}")
        prompt_lines.append("")
        
        # 3. Section focus
        section_name = part_name.replace('[]', '').replace('_', ' ').title()
        prompt_lines.append(f"## Focus Area: {section_name}")
        prompt_lines.append("")
        prompt_lines.append(f"Generate a conversation segment discussing the client's {section_name.lower()}.")
        prompt_lines.append("Include natural dialogue between the advisor and client(s), with specific details and values.")
        prompt_lines.append("")
        
        # 4. Attribute values and examples
        prompt_lines.append("## Attributes to Cover")
        prompt_lines.append("")
        prompt_lines.append("Include discussion of the following attributes where relevant:")
        prompt_lines.append(self.format_attribute_examples(examples))
        prompt_lines.append("")
        
        # 5. Citation examples
        if citations_by_time:
            prompt_lines.append(self.format_citation_examples(citations_by_time))
            prompt_lines.append("")
        
        # 6. Additional guidance
        prompt_lines.append("## Output Requirements")
        prompt_lines.append("")
        prompt_lines.append("1. DON'T USE THE SAME LOCATIONS AND VALUES AS IN THE EXAMPLES. USE DIFFERENT VALUES AND LOCATIONS.")
        prompt_lines.append("1. **Format:** Natural conversational dialogue with speaker labels (ADVISOR:, CLIENT:, CLIENT1:, CLIENT2:)")
        prompt_lines.append("2. **Timestamps:** Include timestamps in format [HH:MM:SS] at natural conversation points")
        prompt_lines.append("3. **Detail:** Include specific numbers, dates, and factual information")
        prompt_lines.append("4. **Natural flow:** The conversation should feel realistic with natural transitions")
        prompt_lines.append("5. **Length:** Generate 15-20 minutes of conversation")
        prompt_lines.append("")
        
        # 7. Additional context from call_time citations
        if citations_by_time:
            prompt_lines.append("## Timeline Guidance")
            prompt_lines.append("")
            prompt_lines.append("The conversation should follow a natural progression. Here's a timeline of topics:")
            prompt_lines.append("")
            
            # Group citations by time ranges
            time_ranges = defaultdict(list)
            for cit in citations_by_time:
                time_sec = self.parse_time(cit['call_time'])
                minute_range = (time_sec // 300) * 5  # 5-minute buckets
                time_ranges[minute_range].append(cit)
            
            for time_range in sorted(time_ranges.keys())[:5]:  # First 5 time buckets
                cits = time_ranges[time_range]
                minutes = time_range // 60
                prompt_lines.append(f"**Around {minutes}-{minutes+5} minutes:**")
                topics = set([c['path'].split('.')[-1].replace('_', ' ') for c in cits[:3]])
                prompt_lines.append(f"  Topics: {', '.join(topics)}")
                prompt_lines.append("")
        
        return '\n'.join(prompt_lines)
    
    def generate_all_prompts(self, output_dir: str = './prompts', instances_per_type: int = 2):
        """Generate prompts for all high-level parts and personas"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate client personas (multiple instances per type)
        print("Generating client personas...")
        personas = self.generate_client_personas(instances_per_type=instances_per_type)
        print(f"Generated {len(personas)} diverse client personas")
        print(f"  - {instances_per_type} instances per persona type")
        print(f"  - Total persona types: {len(personas) // instances_per_type}")
        
        # Extract high-level parts
        print("\nExtracting high-level parts...")
        parts = self.extract_high_level_parts()
        print(f"Found {len(parts)} high-level parts:")
        for part in sorted(parts.keys()):
            print(f"  - {part}")
        
        # Generate prompts
        print("\nGenerating prompts...")
        prompt_count = 0
        
        # Focus on main categories
        main_parts = ['clients[]', 'assets[]', 'pensions[]', 'incomes[]', 
                      'expenses[]', 'loans_and_mortgages[]', 'savings_and_investments[]']
        
        # Use all personas for each part to maximize prompt count
        # This gives us: 7 parts × 14 personas = 98 prompts
        for part in main_parts:
            if part not in parts:
                continue
            
            print(f"\n  Processing {part}...")
            
            # Use all personas for each part
            for persona in personas:
                prompt = self.generate_prompt_for_part(part, persona)
                
                if prompt:
                    # Create directory for this persona if it doesn't exist
                    persona_dir = os.path.join(output_dir, persona['id'])
                    os.makedirs(persona_dir, exist_ok=True)
                    
                    # Save prompt to file inside persona directory
                    part_clean = part.replace('[]', '').replace('_', '-')
                    filename = f"{part_clean}.txt"
                    filepath = os.path.join(persona_dir, filename)
                    
                    with open(filepath, 'w') as f:
                        f.write(prompt)
                    
                    prompt_count += 1
                    print(f"    ✓ Generated: {persona['id']}/{filename}")
        
        print(f"\n{'='*80}")
        print(f"Successfully generated {prompt_count} prompts in {output_dir}/")
        print(f"Organized in {len(personas)} persona directories")
        print(f"{'='*80}")
        
        # Generate summary file
        summary_path = os.path.join(output_dir, '_summary.json')
        summary = {
            'total_prompts': prompt_count,
            'total_personas': len(personas),
            'instances_per_type': instances_per_type,
            'parts': main_parts,
            'file_structure': 'Each persona has a directory containing 7 prompt files',
            'example_structure': {
                'persona_directory': 'prompts/{persona_id}/',
                'files_in_directory': [part.replace('[]', '').replace('_', '-') + '.txt' for part in main_parts]
            },
            'personas': [{'id': p['id'], 'name': p['name'], 'type': p['type'], 'client_names': p['client_names']} for p in personas]
        }
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\nSummary saved to {summary_path}")
        print(f"\nFile structure:")
        print(f"  Each persona has its own directory: prompts/{{persona_id}}/")
        print(f"  Each directory contains 7 files: clients.txt, assets.txt, etc.")
        print(f"  To get all prompts for a person: ls prompts/{{persona_id}}/*.txt")


def main():
    print("="*80)
    print("Transcript Prompt Generator")
    print("="*80)
    print()
    
    generator = TranscriptPromptGenerator()
    
    # Load data
    print("Loading data...")
    combined_path = '/home/igor/test_task/combined_schema_examples_2.json'
    res_paths = [
        '/home/igor/test_task/best/res1.json',
        '/home/igor/test_task/best/res2.json'
    ]
    
    generator.load_data(combined_path, res_paths)
    print(f"✓ Loaded combined schema examples")
    print(f"✓ Loaded {len(res_paths)} result files")
    
    # Generate all prompts
    # For 100+ complete transcripts: transcripts × 7 parts = prompts
    # 17 persona types × 6 instances = 102 personas
    # 102 personas × 7 parts = 714 prompts
    output_dir = '/home/igor/test_task/prompts'
    instances_per_type = 6  # Generate 6 instances of each persona type
    
    print(f"\nTarget: 100+ complete transcripts")
    print(f"Strategy: Each transcript has 7 parts (chunks)")
    print(f"         17 persona types × {instances_per_type} instances = {17 * instances_per_type} personas")
    print(f"         {17 * instances_per_type} personas × 7 parts = {17 * instances_per_type * 7} prompts")
    print()
    
    generator.generate_all_prompts(output_dir, instances_per_type=instances_per_type)
    
    print("\nDone!")


if __name__ == '__main__':
    main()

