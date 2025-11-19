#!/usr/bin/env python3
"""
Script to generate financial fact-find transcripts from prompts using OpenAI API.

Process:
1. For each persona, read all 7 prompt files
2. Call OpenAI API to generate a transcript chunk for each prompt
3. Combine all chunks and call OpenAI again to shuffle/refine the complete transcript
"""

import os
import json
import random
import time
import multiprocessing as mp
from pathlib import Path
from typing import List, Dict, Tuple
from openai import OpenAI


# Worker function for multiprocessing (must be at module level for pickling)
def _process_persona_worker(args: Tuple) -> Dict:
    """Worker function to process a single persona in a separate process"""
    persona_dir, output_dir, skip_if_exists, model, api_key = args
    
    # Create generator instance in worker process
    generator = TranscriptGenerator(api_key=api_key, model=model)
    
    try:
        success = generator.generate_transcript_for_persona(
            persona_dir,
            output_dir,
            skip_if_exists=skip_if_exists
        )
        
        # Return results
        return {
            'persona': persona_dir.name,
            'success': success,
            'skipped': skip_if_exists and (output_dir / f"{persona_dir.name}.txt").exists() and not success,
            'failed': not success and not (skip_if_exists and (output_dir / f"{persona_dir.name}.txt").exists()),
            'chunks_generated': generator.chunks_generated,
            'transcripts_generated': generator.transcripts_generated,
            'tokens': {
                'input': generator.total_input_tokens,
                'output': generator.total_output_tokens,
                'reasoning': generator.total_reasoning_tokens,
                'cached': generator.total_cached_tokens,
                'total': generator.total_tokens
            }
        }
    except Exception as e:
        return {
            'persona': persona_dir.name,
            'success': False,
            'skipped': False,
            'failed': True,
            'error': str(e),
            'chunks_generated': 0,
            'transcripts_generated': 0,
            'tokens': {
                'input': 0,
                'output': 0,
                'reasoning': 0,
                'cached': 0,
                'total': 0
            }
        }


class TranscriptGenerator:
    def __init__(self, api_key: str = None, model: str = "gpt-5.1"):
        """Initialize the transcript generator with OpenAI client"""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.chunks_generated = 0
        self.transcripts_generated = 0
        
        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_reasoning_tokens = 0
        self.total_cached_tokens = 0
        self.total_tokens = 0
        
    def generate_chunk(self, prompt: str, temperature: float = 1.0) -> str:
        """Generate a transcript chunk from a prompt using OpenAI API"""
        try:
            # Build API call parameters
            api_params = {
                "model": self.model,
                "reasoning": {
                    "effort": "high"
                },
                "text": {"verbosity": "high"},
                "input": [
                    {
                        "role": "system",
                        "content": '''
                        You are an expert at generating realistic financial advisor fact find conversations. 
                        Generate natural, professional dialogue that sounds authentic and includes specific details.
                        1. ADVISOR SHOULDN'T DO ANY RECAPS OF THE CONVERSATION, JUST FOLLOW THE CONVERSATION FLOW.
                        2. Keep phrases short. Don't use exact numbers everywhere, use ranges.
                        3. PEOPLE DON'T KNOW EVERYTHING ABOUT THEIR FINANCIAL SITUATION, SO THEY DON'T PROVIDE ALL THE DETAILS ON THE FIRST CALL AT ONCE.
                        4. Keep speaker labels consistent (ADVISOR:, CLIENT:, CLIENT1:, CLIENT2:)
                        5. Make it sound like a real conversation: add repetitions, pauses, clarifications, and natural conversation patterns.
                        6. Add artifacts from speech recognition software to the transcript.
                        7. Maintain all timestamps in format [HH:MM:SS]
                        8. Make sure the conversation feels realistic with natural back-and-forth.
                        9. Some topics may be revisited multiple times. Client may ask follow-up questions and change their preference during a call.
                        10. Ensure topics are interwoven (e.g., mention pensions while discussing income)
                        11. Ensure that client's manner of speaking is consistent with their personality and background.
                        
                        Ensure that all the above requirements are met.'''
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": temperature
            }
            
            response = self.client.responses.create(**api_params)
            
            self.chunks_generated += 1
            
            # Track token usage
            tokens_used = self._extract_token_usage(response)
            self._update_token_totals(tokens_used)
            
            return response.output_text, tokens_used
            
        except Exception as e:
            print(f"Error generating chunk: {e}")
            return None, None
    
    def combine_and_shuffle(self, chunks: List[str], persona_info: Dict, 
                           temperature: float = None) -> str:
        """Combine chunks and call OpenAI to shuffle/refine the complete transcript"""
        
        # Generate random temperature between 0.9 and 1.2 for more variation
        if temperature is None:
            temperature = 1.0
        
        # Combine all chunks
        combined = "\n\n".join([f"=== SECTION {i+1} ===\n{chunk}" 
                                for i, chunk in enumerate(chunks)])
        
        shuffle_prompt = f"""You are creating a realistic financial fact-find transcript by combining and refining the following conversation segments.

CLIENT INFORMATION:
- Name: {persona_info['client_names']}
- Type: {persona_info['type_name']}
- Description: {persona_info['description']}

CONVERSATION SEGMENTS TO COMBINE:
{combined}
"""

        try:
            # Build API call parameters
            api_params = {
                "model": self.model,
                "reasoning": {
                    "effort": "high"
                },
                "input": [
                    {
                        "role": "system",
                        "content": '''
                        You are an expert at creating realistic financial advisor transcripts. Your transcripts sound natural, with topics flowing organically rather than in rigid sections.
                        YOUR TASK:
                            1. Combine all segments into ONE cohesive conversation
                            2. SHUFFLE topics naturally - don't keep them in strict sections
                            3. If it doesn't make sense to this client to discuss a topic, don't include it.
                            4. Some topics may be revisited multiple times. Client may ask follow-up questions and change their preference during a call.
                            5. PEOPLE DON'T KNOW EVERYTHING ABOUT THEIR FINANCIAL SITUATION, SO THEY DON'T PROVIDE ALL THE DETAILS ON THE FIRST CALL AT ONCE.
                            6. Remove 10-20% of the content (omit redundant or less important details)
                            7. Ensure natural flow and transitions between topics
                            8. ADVISOR SHOULDN'T DO ANY RECAPS OF THE CONVERSATION, JUST FOLLOW THE CONVERSATION FLOW.
                            9. Keep speaker labels consistent (ADVISOR:, CLIENT:, CLIENT1:, CLIENT1: [00:00:09], CLIENT2: [00:00:17], etc.)
                            10. Maintain all timestamps in format [HH:MM:SS]
                            11. Make sure the conversation feels realistic with natural back-and-forth
                            12. Include pauses, clarifications, and natural conversation patterns
                            13. Ensure topics are interwoven (e.g., mention pensions while discussing income)

                            IMPORTANT:
                            - This should feel like ONE continuous conversation, not separate sections
                            - Topics should come up naturally, not in a rigid order
                            - Some topics may be revisited multiple times
                            - The advisor should build rapport and ask follow-up questions
                            - Total length: approximately 90-120 minutes of conversation

                            Generate the complete, shuffled transcript.
                        '''
                    },
                    {
                        "role": "user",
                        "content": shuffle_prompt
                    }
                ],
                "temperature": temperature
            }
            
            response = self.client.responses.create(**api_params)
            
            self.transcripts_generated += 1
            
            # Track token usage
            tokens_used = self._extract_token_usage(response)
            self._update_token_totals(tokens_used)
            
            output_text = response.output_text.replace("\n---", "")
            
            return output_text, temperature, tokens_used
            
        except Exception as e:
            print(f"Error combining and shuffling: {e}")
            return None, temperature, None
    
    def generate_transcript_for_persona(self, persona_dir: Path, 
                                       output_dir: Path,
                                       skip_if_exists: bool = True) -> bool:
        """Generate a complete transcript for one persona"""
        
        persona_id = persona_dir.name
        output_file = output_dir / f"{persona_id}.txt"
        
        # Skip if already exists
        if skip_if_exists and output_file.exists():
            print(f"  [SKIP] Skipping {persona_id} (already exists)")
            return False
        
        print(f"\n{'='*80}")
        print(f"Generating transcript for: {persona_id}")
    
        print(f"{'='*80}")
        
        # Read persona metadata from _summary.json
        summary_file = persona_dir.parent / '_summary.json'
        persona_info = self._get_persona_info(summary_file, persona_id)
        
        # Get all prompt files
        prompt_files = sorted(persona_dir.glob("*.txt"))
        
        if not prompt_files:
            print(f"  [ERROR] No prompt files found in {persona_dir}")
            return False
        
        print(f"  Found {len(prompt_files)} prompt files")
        
        # Generate chunks from each prompt
        chunks = []
        for i, prompt_file in enumerate(prompt_files, 1):
            part_name = prompt_file.stem
            print(f"  [{i}/{len(prompt_files)}] Generating chunk: {part_name}...")
            
            with open(prompt_file, 'r') as f:
                prompt = f.read()
            
            result = self.generate_chunk(prompt)
            
            if result and result[0]:
                chunk, tokens = result
                chunks.append(chunk)
                token_info = ""
                if tokens:
                    token_info = f" | Tokens: in={tokens['input_tokens']}, out={tokens['output_tokens']}"
                    if tokens['cached_tokens'] > 0:
                        token_info += f", cached={tokens['cached_tokens']}"
                    if tokens['reasoning_tokens'] > 0:
                        token_info += f", reasoning={tokens['reasoning_tokens']}"
                print(f"      [OK] Generated ({len(chunk)} chars){token_info}")
            else:
                print(f"      [ERROR] Failed")
                return False
            
            # Rate limiting: small delay between requests
            time.sleep(0.5)
        
        # Combine and shuffle all chunks
        print(f"\n  Combining and shuffling {len(chunks)} chunks...")
        result = self.combine_and_shuffle(chunks, persona_info)
        final_transcript, temp_used, tokens = result
        
        if final_transcript:
            # Show token usage for combine step
            if tokens:
                print(f"  [OK] Combine tokens: in={tokens['input_tokens']}, out={tokens['output_tokens']}", end="")
                if tokens['cached_tokens'] > 0:
                    print(f", cached={tokens['cached_tokens']}", end="")
                if tokens['reasoning_tokens'] > 0:
                    print(f", reasoning={tokens['reasoning_tokens']}", end="")
                print()
            # Save the transcript
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Add metadata header
            header = f"""# Financial Fact-Find Transcript
# Persona: {persona_info['client_names']}
# Type: {persona_info['type_name']}
# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
# Temperature: {temp_used}
# Chunks combined: {len(chunks)}
{'='*80}

"""
            
            with open(output_file, 'w') as f:
                f.write(header + final_transcript)
            
            print(f"  [OK] Saved to: {output_file}")
            print(f"  [OK] Length: {len(final_transcript)} chars")
            print(f"  [OK] Temperature used: {temp_used}")
            
            return True
        else:
            print(f"  [ERROR] Failed to generate final transcript")
            return False
    
    def _extract_token_usage(self, response) -> Dict[str, int]:
        """Extract token usage from API response"""
        tokens = {
            'input_tokens': 0,
            'output_tokens': 0,
            'reasoning_tokens': 0,
            'cached_tokens': 0,
            'total_tokens': 0
        }
        
        try:
            usage = response.usage
            tokens['input_tokens'] = getattr(usage, 'input_tokens', 0)
            tokens['output_tokens'] = getattr(usage, 'output_tokens', 0)
            tokens['total_tokens'] = getattr(usage, 'total_tokens', 0)
            
            # Extract reasoning tokens from output_tokens_details
            if hasattr(usage, 'output_tokens_details'):
                details = usage.output_tokens_details
                tokens['reasoning_tokens'] = getattr(details, 'reasoning_tokens', 0)
            
            # Extract cached tokens from input_tokens_details
            if hasattr(usage, 'input_tokens_details'):
                details = usage.input_tokens_details
                tokens['cached_tokens'] = getattr(details, 'cached_tokens', 0)
                
        except Exception as e:
            print(f"  [WARNING] Could not extract token usage: {e}")
        
        return tokens
    
    def _update_token_totals(self, tokens: Dict[str, int]):
        """Update running totals of token usage"""
        if tokens:
            self.total_input_tokens += tokens.get('input_tokens', 0)
            self.total_output_tokens += tokens.get('output_tokens', 0)
            self.total_reasoning_tokens += tokens.get('reasoning_tokens', 0)
            self.total_cached_tokens += tokens.get('cached_tokens', 0)
            self.total_tokens += tokens.get('total_tokens', 0)
    
    def _get_persona_info(self, summary_file: Path, persona_id: str) -> Dict:
        """Get persona information from summary file"""
        try:
            with open(summary_file, 'r') as f:
                summary = json.load(f)
            
            for persona in summary['personas']:
                if persona['id'] == persona_id:
                    return {
                        'client_names': persona['client_names'],
                        'type_name': persona['name'].split(':')[0].strip(),
                        'description': f"{persona['name']}"
                    }
        except:
            pass
        
        # Fallback
        return {
            'client_names': persona_id.replace('_', ' ').title(),
            'type_name': 'Client',
            'description': persona_id
        }
    
    def generate_batch(self, prompts_dir: Path, output_dir: Path, 
                      max_transcripts: int = None,
                      skip_if_exists: bool = True,
                      num_workers: int = None):
        """Generate transcripts for multiple personas using multiprocessing
        
        Args:
            prompts_dir: Directory containing prompt subdirectories
            output_dir: Directory to save generated transcripts
            max_transcripts: Maximum number of transcripts to generate
            skip_if_exists: Skip if transcript already exists
            num_workers: Number of parallel workers (default: CPU count)
        """
        
        prompts_dir = Path(prompts_dir)
        output_dir = Path(output_dir)
        
        # Get all persona directories
        persona_dirs = sorted([d for d in prompts_dir.iterdir() 
                             if d.is_dir() and not d.name.startswith('_')])
        
        if max_transcripts:
            persona_dirs = persona_dirs[:max_transcripts]
        
        # Determine number of workers
        if num_workers is None:
            num_workers = mp.cpu_count()
        
        print(f"\n{'='*80}")
        print(f"TRANSCRIPT GENERATION BATCH (MULTIPROCESSING)")
        print(f"{'='*80}")
        print(f"Prompts directory: {prompts_dir}")
        print(f"Output directory: {output_dir}")
        print(f"Total personas: {len(persona_dirs)}")
        print(f"Parallel workers: {num_workers} (each handles 1 persona at a time)")
        print(f"{'='*80}\n")
        
        # Prepare worker arguments
        worker_args = [
            (persona_dir, output_dir, skip_if_exists, self.model, self.api_key)
            for persona_dir in persona_dirs
        ]
        
        # Process personas in parallel
        results = []
        try:
            with mp.Pool(processes=num_workers) as pool:
                # Use imap for better progress tracking
                for i, result in enumerate(pool.imap(_process_persona_worker, worker_args), 1):
                    results.append(result)
                    
                    # Print progress
                    status = "✓" if result['success'] else ("○" if result['skipped'] else "✗")
                    print(f"[{i}/{len(persona_dirs)}] {status} {result['persona']}")
                    
                    if 'error' in result:
                        print(f"     └─ Error: {result['error']}")
                    
        except KeyboardInterrupt:
            print("\n\n[WARNING] Interrupted by user")
            pool.terminate()
            pool.join()
        
        # Aggregate results
        successful = sum(1 for r in results if r['success'])
        skipped = sum(1 for r in results if r['skipped'])
        failed = sum(1 for r in results if r['failed'])
        
        # Aggregate token usage
        total_chunks = sum(r['chunks_generated'] for r in results)
        total_transcripts = sum(r['transcripts_generated'] for r in results)
        total_input_tokens = sum(r['tokens']['input'] for r in results)
        total_output_tokens = sum(r['tokens']['output'] for r in results)
        total_reasoning_tokens = sum(r['tokens']['reasoning'] for r in results)
        total_cached_tokens = sum(r['tokens']['cached'] for r in results)
        total_tokens = sum(r['tokens']['total'] for r in results)
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"BATCH GENERATION COMPLETE")
        print(f"{'='*80}")
        print(f"Successful: {successful}")
        print(f"Skipped: {skipped}")
        print(f"Failed: {failed}")
        print(f"Total chunks generated: {total_chunks}")
        print(f"Total transcripts: {total_transcripts}")
        print(f"\n{'='*80}")
        print(f"TOKEN USAGE SUMMARY")
        print(f"{'='*80}")
        print(f"Input tokens:     {total_input_tokens:,}")
        if total_cached_tokens > 0:
            print(f"Cached tokens:    {total_cached_tokens:,}")
        print(f"Output tokens:    {total_output_tokens:,}")
        if total_reasoning_tokens > 0:
            print(f"Reasoning tokens: {total_reasoning_tokens:,}")
        print(f"Total tokens:     {total_tokens:,}")
        
        # Estimate cost (gpt-5.1 pricing)
        if total_tokens > 0:
            # gpt-5.1: Input $1.25/1M, Cached $0.125/1M, Output $10/1M
            uncached_input = total_input_tokens - total_cached_tokens
            estimated_cost = (uncached_input / 1_000_000 * 1.25 + 
                            total_cached_tokens / 1_000_000 * 0.125 +
                            total_output_tokens / 1_000_000 * 10.00)
            print(f"\nEstimated cost (gpt-5.1 rates): ${estimated_cost:.2f}")
            if total_cached_tokens > 0:
                # Calculate savings: difference between regular and cached price
                savings = total_cached_tokens / 1_000_000 * (1.25 - 0.125)
                print(f"Savings from caching: ${savings:.2f}")
        print(f"{'='*80}\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate financial transcripts from prompts using OpenAI API"
    )
    parser.add_argument(
        '--prompts-dir',
        default='/home/igor/test_task/prompts',
        help='Directory containing prompt subdirectories'
    )
    parser.add_argument(
        '--output-dir',
        default='/home/igor/test_task/transcripts',
        help='Directory to save generated transcripts'
    )
    parser.add_argument(
        '--persona',
        help='Generate transcript for specific persona only'
    )
    parser.add_argument(
        '--max',
        type=int,
        help='Maximum number of transcripts to generate'
    )
    parser.add_argument(
        '--model',
        default='gpt-5.1',
        help='OpenAI model to use (default: gpt-5)'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing transcripts'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of parallel workers (default: CPU count)'
    )
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = TranscriptGenerator(model=args.model)
    
    prompts_dir = Path(args.prompts_dir)
    output_dir = Path(args.output_dir)
    
    if args.persona:
        # Generate for single persona
        persona_dir = prompts_dir / args.persona
        if not persona_dir.exists():
            print(f"[ERROR] Persona directory not found: {persona_dir}")
            return
        
        generator.generate_transcript_for_persona(
            persona_dir,
            output_dir,
            skip_if_exists=not args.overwrite
        )
    else:
        # Generate batch
        generator.generate_batch(
            prompts_dir,
            output_dir,
            max_transcripts=args.max,
            skip_if_exists=not args.overwrite,
            num_workers=args.workers
        )


if __name__ == '__main__':
    # Set multiprocessing start method (required for proper pickling)
    try:
        mp.set_start_method('spawn')
    except RuntimeError:
        # Already set, ignore
        pass
    main()

