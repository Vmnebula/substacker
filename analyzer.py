import pandas as pd
import hashlib
from typing import Dict, List, Tuple, Generator
import json
from datetime import datetime, timedelta
from cachetools import LRUCache

class OpenAIWasteAnalyzer:
    """Identifies waste patterns in LLM API usage with multi-provider support"""
    
    def __init__(self):
        # Multi-provider pricing as of Oct 2025 (per 1K tokens)
        self.pricing = {
            # OpenAI
            'gpt-4': {'input': 0.03, 'output': 0.06, 'provider': 'openai'},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03, 'provider': 'openai'},
            'gpt-4-turbo-preview': {'input': 0.01, 'output': 0.03, 'provider': 'openai'},
            'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015, 'provider': 'openai'},
            'gpt-3.5-turbo-16k': {'input': 0.003, 'output': 0.004, 'provider': 'openai'},
            
            # Anthropic Claude
            'claude-3-opus': {'input': 0.015, 'output': 0.075, 'provider': 'anthropic'},
            'claude-3-opus-20240229': {'input': 0.015, 'output': 0.075, 'provider': 'anthropic'},
            'claude-3-sonnet': {'input': 0.003, 'output': 0.015, 'provider': 'anthropic'},
            'claude-3-sonnet-20240229': {'input': 0.003, 'output': 0.015, 'provider': 'anthropic'},
            'claude-3-haiku': {'input': 0.00025, 'output': 0.00125, 'provider': 'anthropic'},
            'claude-3-haiku-20240307': {'input': 0.00025, 'output': 0.00125, 'provider': 'anthropic'},
            'claude-2.1': {'input': 0.008, 'output': 0.024, 'provider': 'anthropic'},
            'claude-2': {'input': 0.008, 'output': 0.024, 'provider': 'anthropic'},
            
            # Google Gemini
            'gemini-pro': {'input': 0.00025, 'output': 0.0005, 'provider': 'google'},
            'gemini-pro-vision': {'input': 0.00025, 'output': 0.0005, 'provider': 'google'},
            'gemini-1.5-pro': {'input': 0.00125, 'output': 0.00375, 'provider': 'google'},
            'gemini-1.5-flash': {'input': 0.000075, 'output': 0.0003, 'provider': 'google'},
            
            # Azure OpenAI (same as OpenAI pricing)
            'azure-gpt-4': {'input': 0.03, 'output': 0.06, 'provider': 'azure'},
            'azure-gpt-4-turbo': {'input': 0.01, 'output': 0.03, 'provider': 'azure'},
            'azure-gpt-35-turbo': {'input': 0.0005, 'output': 0.0015, 'provider': 'azure'},
        }
        
        # Task complexity mapping
        self.simple_task_patterns = [
            'extract', 'classify', 'yes/no', 'true/false', 
            'sentiment', 'summary', 'translate', 'format'
        ]
        
        # LRU cache for duplicate detection (max 10000 hashes)
        self.prompt_hash_cache = LRUCache(maxsize=10000)
        self.batch_size = 1000  # Process in batches
        self.auto_generated_mapping = None  # Store auto-generated team mapping
    
    def _detect_provider(self, model_name: str) -> str:
        """Auto-detect provider from model name"""
        model_lower = str(model_name).lower()
        
        if model_lower.startswith('gpt-') or model_lower.startswith('davinci') or model_lower.startswith('text-'):
            return 'openai'
        elif model_lower.startswith('claude'):
            return 'anthropic'
        elif model_lower.startswith('gemini'):
            return 'google'
        elif model_lower.startswith('azure-'):
            return 'azure'
        else:
            return 'unknown'
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to handle case variations and spaces"""
        # Create a mapping of lowercase column names to actual column names
        column_mapping = {
            'model': None,
            'prompt_tokens': None,
            'completion_tokens': None,
            'prompt': None,
            'system_prompt': None,
            'team': None,
            'department': None,
            'api_key': None,
            'user_email': None,
            'customer_id': None
        }
        
        # Find matching columns (case-insensitive)
        for actual_col in df.columns:
            lower_col = actual_col.lower().strip().replace(' ', '_')
            
            if lower_col == 'model':
                column_mapping['model'] = actual_col
            elif lower_col in ['prompt_tokens', 'input_tokens', 'prompt_token']:
                column_mapping['prompt_tokens'] = actual_col
            elif lower_col in ['completion_tokens', 'output_tokens', 'completion_token']:
                column_mapping['completion_tokens'] = actual_col
            elif lower_col == 'prompt':
                column_mapping['prompt'] = actual_col
            elif lower_col in ['system_prompt', 'systemprompt']:
                column_mapping['system_prompt'] = actual_col
            elif lower_col in ['team', 'department', 'team_name', 'dept']:
                if column_mapping['team'] is None:  # Prefer 'team' over 'department'
                    column_mapping['team'] = actual_col
            elif lower_col in ['api_key', 'apikey', 'key']:
                column_mapping['api_key'] = actual_col
            elif lower_col in ['user_email', 'email', 'user']:
                column_mapping['user_email'] = actual_col
            elif lower_col in ['customer_id', 'customerid', 'customer']:
                column_mapping['customer_id'] = actual_col
        
        # Rename columns that were found
        rename_dict = {}
        for standard_name, actual_col in column_mapping.items():
            if actual_col and actual_col != standard_name:
                rename_dict[actual_col] = standard_name
        
        if rename_dict:
            df = df.rename(columns=rename_dict)
        
        # AUTO-GENERATE TEAM COLUMN IF MISSING (CRITICAL FIX)
        if 'team' not in df.columns:
            if 'api_key' in df.columns:
                # Map API keys to teams
                unique_keys = df['api_key'].unique()
                key_to_team = {key: f"Team-{chr(65+i)}" for i, key in enumerate(unique_keys[:26])}  # A-Z
                # Handle more than 26 teams
                if len(unique_keys) > 26:
                    for i, key in enumerate(unique_keys[26:]):
                        key_to_team[key] = f"Team-{i+27}"
                df['team'] = df['api_key'].map(key_to_team)
                self.auto_generated_mapping = {
                    'method': 'api_key',
                    'mapping': key_to_team
                }
            elif 'user_email' in df.columns:
                # Group by email domain
                df['team'] = df['user_email'].apply(
                    lambda x: x.split('@')[0].split('.')[0].title() if pd.notna(x) and '@' in str(x) else 'Unknown'
                )
                self.auto_generated_mapping = {
                    'method': 'email_domain',
                    'mapping': 'Generated from email addresses'
                }
            elif 'customer_id' in df.columns:
                # Group by customer
                df['team'] = df['customer_id'].apply(lambda x: f"Customer-{x}" if pd.notna(x) else 'Unknown')
                self.auto_generated_mapping = {
                    'method': 'customer_id',
                    'mapping': 'Generated from customer IDs'
                }
            else:
                # Fallback: Single team
                df['team'] = 'All Teams'
                self.auto_generated_mapping = {
                    'method': 'default',
                    'mapping': 'No team data found - all requests grouped together'
                }
        
        return df
    
    def analyze_usage(self, df: pd.DataFrame) -> Dict:
        """Main analysis function with multi-provider support"""
        
        # Normalize column names (handle case-insensitive and space variations)
        df = self._normalize_columns(df)
        
        # Validate required columns
        required_cols = ['model', 'prompt_tokens', 'completion_tokens']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            error_msg = f"""
ERROR: This tool analyzes LLM API usage data. The uploaded file has incorrect format.

REQUIRED COLUMNS (must be present):
- model (e.g., gpt-4, claude-3-opus, gemini-pro)
- prompt_tokens (number of input tokens)
- completion_tokens (number of output tokens)

OPTIONAL COLUMNS (for detailed analysis):
- prompt (the actual prompt text)
- system_prompt (the system message)
- team (team/department name for attribution)
- api_key (for auto-team mapping)
- user_email (for auto-team mapping)
- customer_id (for customer attribution)

YOUR FILE COLUMNS: {', '.join(df.columns)}

EXAMPLE FORMAT:
model,prompt_tokens,completion_tokens,team
gpt-4,100,50,Engineering
claude-3-opus,200,100,Marketing
gemini-pro,50,25,Data Science

Please upload a CSV or JSON file from your LLM API logs.
            """
            return {
                'total_cost': 0,
                'total_requests': 0,
                'waste_identified': 0,
                'savings_potential': 0,
                'patterns': [],
                'recommendations': [],
                'team_breakdown': {},
                'error': error_msg.strip()
            }
        
        results = {
            'total_cost': 0,
            'total_requests': len(df),
            'waste_identified': 0,
            'savings_potential': 0,
            'patterns': [],
            'recommendations': [],
            'team_breakdown': {},  # Attribution by team
            'provider_breakdown': {},  # NEW: Costs by provider
            'auto_generated_teams': self.auto_generated_mapping  # Show if teams were auto-generated
        }
        
        # Add default 'prompt' column if missing (for backward compatibility)
        if 'prompt' not in df.columns:
            df['prompt'] = 'N/A'
        
        # Add default 'system_prompt' column if missing
        if 'system_prompt' not in df.columns:
            df['system_prompt'] = ''
        
        # Calculate total cost
        results['total_cost'] = self._calculate_total_cost(df)
        
        # Calculate costs by team
        results['team_breakdown'] = self._calculate_costs_by_team(df)
        
        # Calculate costs by provider (NEW: Multi-provider support)
        results['provider_breakdown'] = self._calculate_costs_by_provider(df)
        
        # 1. Detect repeated identical prompts
        duplicate_waste = self._find_duplicate_prompts(df)
        results['patterns'].append(duplicate_waste)
        
        # 2. Detect overkill model usage
        model_waste = self._find_model_overkill(df)
        results['patterns'].append(model_waste)
        
        # 3. Detect repeated system prompts
        system_waste = self._find_system_prompt_waste(df)
        results['patterns'].append(system_waste)
        
        # 4. Detect cache-able patterns
        cache_waste = self._find_cacheable_patterns(df)
        results['patterns'].append(cache_waste)
        
        # 5. Detect token inefficiencies
        token_waste = self._find_token_waste(df)
        results['patterns'].append(token_waste)
        
        # Calculate total waste
        results['waste_identified'] = sum(p['waste_amount'] for p in results['patterns'])
        results['savings_potential'] = results['waste_identified'] / results['total_cost'] * 100 if results['total_cost'] else 0
        
        # Add percentage and name fields to each pattern
        for pattern in results['patterns']:
            pattern['percentage'] = (pattern['waste_amount'] / results['total_cost'] * 100) if results['total_cost'] else 0
            if 'type' in pattern:
                pattern['name'] = pattern['type']  # Ensure 'name' field exists for frontend
        
        # Generate recommendations
        results['recommendations'] = self._generate_recommendations(results['patterns'])
        
        return results
    
    def _calculate_costs_by_team(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate total cost by team"""
        team_costs = {}
        
        for _, row in df.iterrows():
            team = row.get('team', 'Other')
            cost = self._calculate_row_cost(row)
            
            if team not in team_costs:
                team_costs[team] = 0
            team_costs[team] += cost
        
        # Sort by cost (descending)
        return dict(sorted(team_costs.items(), key=lambda x: x[1], reverse=True))
    
    def _calculate_costs_by_provider(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """Calculate total cost by provider (NEW: Multi-provider support)"""
        provider_costs = {}
        
        for _, row in df.iterrows():
            model = row.get('model', '')
            provider = self._detect_provider(model)
            cost = self._calculate_row_cost(row)
            
            if provider not in provider_costs:
                provider_costs[provider] = {
                    'cost': 0,
                    'requests': 0,
                    'tokens': 0
                }
            
            provider_costs[provider]['cost'] += cost
            provider_costs[provider]['requests'] += 1
            provider_costs[provider]['tokens'] += row.get('prompt_tokens', 0) + row.get('completion_tokens', 0)
        
        # Sort by cost (descending)
        return dict(sorted(provider_costs.items(), key=lambda x: x[1]['cost'], reverse=True))
    
    def _calculate_total_cost(self, df: pd.DataFrame) -> float:
        """Calculate total API spend across all providers"""
        total = 0
        for _, row in df.iterrows():
            total += self._calculate_row_cost(row)
        return total
    
    def _find_duplicate_prompts(self, df: pd.DataFrame) -> Dict:
        """Find identical prompts that could be cached"""
        
        # Hash prompts to find duplicates
        df['prompt_hash'] = df['prompt'].apply(lambda x: hashlib.md5(str(x).encode()).hexdigest())
        
        # Calculate waste (keep 1, rest are waste)
        waste = 0
        examples = []
        
        for hash_val, group in df.groupby('prompt_hash'):
            if len(group) > 1:
                # Cost of duplicates (excluding first occurrence)
                duplicate_cost = self._calculate_group_cost(group.iloc[1:])
                waste += duplicate_cost
                
                if duplicate_cost > 10 and len(examples) < 3:  # Show top examples
                    examples.append({
                        'prompt': group.iloc[0]['prompt'][:100] + '...',
                        'count': len(group),
                        'waste': duplicate_cost
                    })
        
        return {
            'name': 'Duplicate Prompts',
            'type': 'Duplicate Prompts',
            'description': 'Identical prompts that could be cached',
            'waste_amount': waste,
            'amount_wasted': waste,
            'percentage': 0,  # Will be calculated in main function
            'fix': 'Implement semantic caching (Redis/Memcached)',
            'examples': examples,
            'effort': 'LOW',
            'savings_range': '20-30%'
        }
    
    def _find_model_overkill(self, df: pd.DataFrame) -> Dict:
        """Find expensive model usage for simple tasks (multi-provider aware)"""
        
        waste = 0
        examples = []
        
        for _, row in df.iterrows():
            model = str(row.get('model', '')).lower()
            prompt_lower = str(row.get('prompt', '')).lower()
            
            # Check if using expensive model
            is_expensive = any(x in model for x in ['gpt-4', 'claude-3-opus', 'claude-opus', 'gemini-1.5-pro'])
            
            # Check if it's a simple task
            is_simple = any(pattern in prompt_lower for pattern in self.simple_task_patterns)
            
            if is_expensive and is_simple:
                # Calculate potential savings with cheaper alternative
                current_cost = self._calculate_row_cost(row)
                
                # Suggest cheaper alternative based on provider
                provider = self._detect_provider(model)
                if provider == 'openai':
                    suggested_model = 'gpt-3.5-turbo'
                elif provider == 'anthropic':
                    suggested_model = 'claude-3-haiku'
                elif provider == 'google':
                    suggested_model = 'gemini-1.5-flash'
                else:
                    suggested_model = 'gpt-3.5-turbo'
                
                potential_cost = self._calculate_row_cost(row, override_model=suggested_model)
                savings = current_cost - potential_cost
                waste += savings
                
                if len(examples) < 3:
                    examples.append({
                        'prompt': row.get('prompt', '')[:100] + '...',
                        'current_model': row.get('model', ''),
                        'suggested_model': suggested_model,
                        'savings': savings
                    })
        
        return {
            'name': 'Model Overkill',
            'type': 'Model Overkill',
            'description': 'Using expensive models for simple tasks',
            'waste_amount': waste,
            'amount_wasted': waste,
            'percentage': 0,
            'fix': 'Route simple queries to cheaper models',
            'examples': examples,
            'effort': 'LOW',
            'savings_range': '60-95%'
        }
    
    def _find_system_prompt_waste(self, df: pd.DataFrame) -> Dict:
        """Find repeated system prompts that could be optimized"""
        
        waste = 0
        system_prompts = {}
        
        for _, row in df.iterrows():
            system_prompt = row.get('system_prompt', '')
            if isinstance(system_prompt, str) and system_prompt and len(system_prompt) > 500:  # Long system prompts
                prompt_hash = hashlib.md5(system_prompt.encode()).hexdigest()
                
                if prompt_hash not in system_prompts:
                    system_prompts[prompt_hash] = {
                        'text': system_prompt,
                        'count': 0,
                        'total_tokens': 0
                    }
                
                system_prompts[prompt_hash]['count'] += 1
                system_prompts[prompt_hash]['total_tokens'] += len(system_prompt) / 4  # Rough token estimate
        
        # Calculate waste from repeated long system prompts
        for hash_val, data in system_prompts.items():
            if data['count'] > 10:  # Repeated more than 10 times
                # Could be shortened or cached
                waste += (data['total_tokens'] * 0.7 * 0.001)  # Assume 70% reduction possible
        
        return {
            'name': 'Bloated Prompts',
            'type': 'System Prompt Redundancy',
            'description': 'Large system prompts repeated every call',
            'waste_amount': waste,
            'amount_wasted': waste,
            'percentage': 0,
            'fix': 'Use conversation threading or prompt compression',
            'examples': [{'repeated': f"{v['count']} times", 'tokens': v['total_tokens']} 
                        for v in list(system_prompts.values())[:3]],
            'effort': 'MEDIUM',
            'savings_range': '10-20%'
        }
    
    def _find_cacheable_patterns(self, df: pd.DataFrame) -> Dict:
        """Find semantically similar queries that could share responses"""
        
        # Simple pattern matching for common cacheable queries
        cacheable_patterns = [
            'what is', 'how do', 'define', 'explain', 
            'list', 'what are', 'describe', 'tell me about'
        ]
        
        cacheable_count = 0
        waste = 0
        
        for _, row in df.iterrows():
            prompt_lower = str(row.get('prompt', '')).lower()
            if any(pattern in prompt_lower for pattern in cacheable_patterns):
                cacheable_count += 1
                # Estimate 25% could be cached
                waste += self._calculate_row_cost(row) * 0.25
        
        return {
            'name': 'High Token Usage',
            'type': 'Cacheable Queries',
            'description': 'Semantically similar queries that could share responses',
            'waste_amount': waste,
            'amount_wasted': waste,
            'percentage': 0,
            'fix': 'Implement semantic similarity caching',
            'examples': [{'pattern': 'FAQ-style questions', 'count': cacheable_count}],
            'effort': 'MEDIUM',
            'savings_range': '15-25%'
        }
    
    def _find_token_waste(self, df: pd.DataFrame) -> Dict:
        """Find token inefficiencies"""
        
        waste = 0
        verbose_examples = []
        
        for _, row in df.iterrows():
            prompt = str(row.get('prompt', ''))
            
            # Check for verbose patterns
            verbose_patterns = [
                ('    ', ' '),  # Multiple spaces
                ('\n\n\n', '\n\n'),  # Multiple newlines
                ('please please', 'please'),  # Redundant words
            ]
            
            original_len = len(prompt)
            cleaned = prompt
            for pattern, replacement in verbose_patterns:
                cleaned = cleaned.replace(pattern, replacement)
            
            if original_len and len(cleaned) < original_len * 0.9:  # 10% reduction possible
                token_reduction = (original_len - len(cleaned)) / 4  # Rough token estimate
                waste += token_reduction * 0.001
                
                if len(verbose_examples) < 3:
                    verbose_examples.append({
                        'original_tokens': original_len // 4,
                        'optimized_tokens': len(cleaned) // 4,
                        'reduction': f"{(1 - len(cleaned)/original_len)*100:.1f}%"
                    })
        
        return {
            'name': 'Large Context Windows',
            'type': 'Token Inefficiency',
            'description': 'Verbose prompts with redundant tokens',
            'waste_amount': waste,
            'amount_wasted': waste,
            'percentage': 0,
            'fix': 'Implement prompt compression and cleaning',
            'examples': verbose_examples,
            'effort': 'LOW',
            'savings_range': '5-15%'
        }
    
    def _calculate_row_cost(self, row: pd.Series, override_model: str = None) -> float:
        """Calculate cost for a single API call (multi-provider aware)"""
        model = override_model or row.get('model', 'gpt-3.5-turbo')
        model_lower = str(model).lower()
        
        # Find pricing (exact match or closest match)
        model_pricing = None
        if model_lower in self.pricing:
            model_pricing = self.pricing[model_lower]
        else:
            # Try to find closest match
            for price_model in self.pricing.keys():
                if price_model in model_lower or model_lower in price_model:
                    model_pricing = self.pricing[price_model]
                    break
        
        # Fallback to gpt-3.5-turbo if model not found
        if not model_pricing:
            model_pricing = self.pricing['gpt-3.5-turbo']
            
        input_tokens = row.get('prompt_tokens', 0)
        output_tokens = row.get('completion_tokens', 0)
        
        cost = (input_tokens * model_pricing['input'] / 1000)
        cost += (output_tokens * model_pricing['output'] / 1000)
        return cost
    
    def _calculate_group_cost(self, group: pd.DataFrame) -> float:
        """Calculate total cost for a group of API calls"""
        return sum(self._calculate_row_cost(row) for _, row in group.iterrows())
    
    def _generate_recommendations(self, patterns: List[Dict]) -> List[Dict]:
        """Generate actionable recommendations based on patterns"""
        
        recommendations = []
        total_waste = sum(p['waste_amount'] for p in patterns)
        
        # Sort patterns by waste amount
        patterns_sorted = sorted(patterns, key=lambda x: x['waste_amount'], reverse=True)
        
        for i, pattern in enumerate(patterns_sorted[:3]):  # Top 3 recommendations
            if pattern['waste_amount'] > 0:
                recommendations.append({
                    'priority': i + 1,
                    'action': pattern['fix'],
                    'impact': f"${pattern['waste_amount']:.2f}",
                    'effort': pattern['effort'],
                    'expected_savings': pattern['savings_range']
                })

        return recommendations
