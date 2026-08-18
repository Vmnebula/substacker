"""
 Cost Analyzer
"""

import hashlib
import logging
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

import pandas as pd
from cachetools import LRUCache

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Provider(Enum):
    """Enum for LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    UNKNOWN = "unknown"


@dataclass
class ModelPricing:
    """Immutable pricing data with validation"""
    input_price: Decimal
    output_price: Decimal
    provider: Provider
    
    def __post_init__(self):
        # Validate on creation
        if self.input_price < 0 or self.output_price < 0:
            raise ValueError("Pricing cannot be negative")


class CostAnalyzer:
    """
    Multi-provider LLM cost analyzer
    
    Features:
    - Decimal precision for monetary calculations (no floating point errors)
    - Strict input validation with clear error messages
    - Robust model name normalization
    - Unknown model tracking
    - Comprehensive logging
    - Auto-team mapping from API keys, emails, or customer IDs
    """
    
    def __init__(self):
        self.pricing = self._initialize_pricing()
        self.model_cache = {}  # Cache normalized model lookups for performance
        self.unknown_models = set()  # Track unknown models
        self.auto_generated_mapping = None
        
        # Task complexity mapping - Simple task indicators
        self.simple_task_patterns = [
            'extract', 'classify', 'yes/no', 'true/false', 
            'sentiment', 'summary', 'translate', 'format',
            'convert', 'choose', 'select', 'pick', 'is this',
            'calculate', 'count', 'find the', 'what is'
        ]
        
        # Complex task exclusion patterns
        self.complex_task_patterns = [
            'detailed analysis', 'comprehensive', 'multi-step', 'elaborate',
            'in-depth', 'thorough', 'complex reasoning', 'sophisticated', 'advanced',
            'explain in detail', 'provide reasoning', 'step by step',
            'analyze all', 'consider multiple', 'evaluate various'
        ]
        
        # Prompt hash cache for duplicate detection
        self.prompt_hash_cache = LRUCache(maxsize=10000)
        
    def _initialize_pricing(self) -> dict[str, ModelPricing]:
        """Per-1K-token list prices, keyed by normalised model name.

        Verified against provider pricing pages on 2026-08-18:
          OpenAI     https://developers.openai.com/api/docs/pricing
          Anthropic  https://claude.com/pricing#api
          Gemini     https://ai.google.dev/gemini-api/docs/pricing

        Two caveats worth knowing before you trust a total:

        - These are standard list prices. Batch, cached-input, and committed-use
          discounts are not modelled, so a real invoice is usually lower.
        - Some models are priced in tiers by context length (Gemini Pro above 200K
          input tokens, for example). This table stores the base tier only, so very
          long-context traffic is under-counted. Tiered pricing is tracked in
          https://github.com/Vmnebula/substacker/issues.

        Retired models are kept so that historical exports still price correctly.
        """
        return {
            # ---------------- OpenAI ----------------
            'gpt-5.6-sol': ModelPricing(Decimal('0.005'), Decimal('0.030'), Provider.OPENAI),
            'gpt-5.6-terra': ModelPricing(Decimal('0.002'), Decimal('0.012'), Provider.OPENAI),
            'gpt-5.6-luna': ModelPricing(Decimal('0.0002'), Decimal('0.0012'), Provider.OPENAI),
            'gpt-5.5': ModelPricing(Decimal('0.005'), Decimal('0.030'), Provider.OPENAI),
            'gpt-5.5-pro': ModelPricing(Decimal('0.030'), Decimal('0.180'), Provider.OPENAI),
            'gpt-5.4': ModelPricing(Decimal('0.0025'), Decimal('0.015'), Provider.OPENAI),
            'gpt-5.4-mini': ModelPricing(Decimal('0.00075'), Decimal('0.0045'), Provider.OPENAI),
            'gpt-5.4-nano': ModelPricing(Decimal('0.0002'), Decimal('0.00125'), Provider.OPENAI),
            'gpt-5.4-pro': ModelPricing(Decimal('0.030'), Decimal('0.180'), Provider.OPENAI),
            'gpt-5.2': ModelPricing(Decimal('0.00175'), Decimal('0.014'), Provider.OPENAI),
            'gpt-5.2-pro': ModelPricing(Decimal('0.021'), Decimal('0.168'), Provider.OPENAI),
            'gpt-5.1': ModelPricing(Decimal('0.00125'), Decimal('0.010'), Provider.OPENAI),
            'gpt-5': ModelPricing(Decimal('0.00125'), Decimal('0.010'), Provider.OPENAI),
            'gpt-5-mini': ModelPricing(Decimal('0.00025'), Decimal('0.002'), Provider.OPENAI),
            'gpt-5-nano': ModelPricing(Decimal('0.00005'), Decimal('0.0004'), Provider.OPENAI),
            'gpt-5-pro': ModelPricing(Decimal('0.015'), Decimal('0.120'), Provider.OPENAI),
            'gpt-4.1': ModelPricing(Decimal('0.002'), Decimal('0.008'), Provider.OPENAI),
            'gpt-4.1-mini': ModelPricing(Decimal('0.0004'), Decimal('0.0016'), Provider.OPENAI),
            'gpt-4.1-nano': ModelPricing(Decimal('0.0001'), Decimal('0.0004'), Provider.OPENAI),
            'gpt-4o': ModelPricing(Decimal('0.0025'), Decimal('0.010'), Provider.OPENAI),
            'gpt-4o-mini': ModelPricing(Decimal('0.00015'), Decimal('0.0006'), Provider.OPENAI),
            'o1': ModelPricing(Decimal('0.015'), Decimal('0.060'), Provider.OPENAI),
            'o1-pro': ModelPricing(Decimal('0.150'), Decimal('0.600'), Provider.OPENAI),
            'o3': ModelPricing(Decimal('0.002'), Decimal('0.008'), Provider.OPENAI),
            'o3-pro': ModelPricing(Decimal('0.020'), Decimal('0.080'), Provider.OPENAI),
            'o3-mini': ModelPricing(Decimal('0.0011'), Decimal('0.0044'), Provider.OPENAI),
            'o4-mini': ModelPricing(Decimal('0.0011'), Decimal('0.0044'), Provider.OPENAI),
            # Retired, retained for historical exports
            'gpt-4': ModelPricing(Decimal('0.030'), Decimal('0.060'), Provider.OPENAI),
            'gpt-4-turbo': ModelPricing(Decimal('0.010'), Decimal('0.030'), Provider.OPENAI),
            'gpt-4-turbo-preview': ModelPricing(Decimal('0.010'), Decimal('0.030'), Provider.OPENAI),
            'gpt-3.5-turbo': ModelPricing(Decimal('0.0005'), Decimal('0.0015'), Provider.OPENAI),
            'gpt-3.5-turbo-16k': ModelPricing(Decimal('0.003'), Decimal('0.004'), Provider.OPENAI),

            # ---------------- Anthropic ----------------
            'claude-fable-5': ModelPricing(Decimal('0.010'), Decimal('0.050'), Provider.ANTHROPIC),
            'claude-opus-5': ModelPricing(Decimal('0.005'), Decimal('0.025'), Provider.ANTHROPIC),
            'claude-opus-4-8': ModelPricing(Decimal('0.005'), Decimal('0.025'), Provider.ANTHROPIC),
            'claude-opus-4-7': ModelPricing(Decimal('0.005'), Decimal('0.025'), Provider.ANTHROPIC),
            'claude-opus-4-6': ModelPricing(Decimal('0.005'), Decimal('0.025'), Provider.ANTHROPIC),
            'claude-sonnet-5': ModelPricing(Decimal('0.003'), Decimal('0.015'), Provider.ANTHROPIC),
            'claude-sonnet-4-6': ModelPricing(Decimal('0.003'), Decimal('0.015'), Provider.ANTHROPIC),
            'claude-haiku-4-5': ModelPricing(Decimal('0.001'), Decimal('0.005'), Provider.ANTHROPIC),
            # Retired, retained for historical exports
            'claude-3-opus': ModelPricing(Decimal('0.015'), Decimal('0.075'), Provider.ANTHROPIC),
            'claude-3-opus-20240229': ModelPricing(Decimal('0.015'), Decimal('0.075'), Provider.ANTHROPIC),
            'claude-3-sonnet': ModelPricing(Decimal('0.003'), Decimal('0.015'), Provider.ANTHROPIC),
            'claude-3-sonnet-20240229': ModelPricing(Decimal('0.003'), Decimal('0.015'), Provider.ANTHROPIC),
            'claude-3-haiku': ModelPricing(Decimal('0.00025'), Decimal('0.00125'), Provider.ANTHROPIC),
            'claude-3-haiku-20240307': ModelPricing(Decimal('0.00025'), Decimal('0.00125'), Provider.ANTHROPIC),
            'claude-2.1': ModelPricing(Decimal('0.008'), Decimal('0.024'), Provider.ANTHROPIC),
            'claude-2': ModelPricing(Decimal('0.008'), Decimal('0.024'), Provider.ANTHROPIC),

            # ---------------- Google Gemini ----------------
            'gemini-3.7-flash': ModelPricing(Decimal('0.00075'), Decimal('0.00375'), Provider.GOOGLE),
            'gemini-3.6-flash': ModelPricing(Decimal('0.00075'), Decimal('0.00375'), Provider.GOOGLE),
            'gemini-3.5-flash': ModelPricing(Decimal('0.0015'), Decimal('0.009'), Provider.GOOGLE),
            'gemini-3.5-flash-lite': ModelPricing(Decimal('0.0003'), Decimal('0.0025'), Provider.GOOGLE),
            'gemini-3.1-pro-preview': ModelPricing(Decimal('0.002'), Decimal('0.012'), Provider.GOOGLE),
            'gemini-3.1-flash-lite': ModelPricing(Decimal('0.00025'), Decimal('0.0015'), Provider.GOOGLE),
            'gemini-2.5-pro': ModelPricing(Decimal('0.00125'), Decimal('0.010'), Provider.GOOGLE),
            'gemini-2.5-flash': ModelPricing(Decimal('0.0003'), Decimal('0.0025'), Provider.GOOGLE),
            'gemini-2.5-flash-lite': ModelPricing(Decimal('0.0001'), Decimal('0.0004'), Provider.GOOGLE),
            # Retired, retained for historical exports
            'gemini-1.5-pro': ModelPricing(Decimal('0.00125'), Decimal('0.00375'), Provider.GOOGLE),
            'gemini-1.5-flash': ModelPricing(Decimal('0.000075'), Decimal('0.0003'), Provider.GOOGLE),
            'gemini-pro': ModelPricing(Decimal('0.00025'), Decimal('0.0005'), Provider.GOOGLE),
            'gemini-pro-vision': ModelPricing(Decimal('0.00025'), Decimal('0.0005'), Provider.GOOGLE),

            # ---------------- Azure OpenAI ----------------
            # Azure bills the same list rates as OpenAI for the equivalent model, but
            # reports names without dots, for example gpt-35-turbo.
            'azure-gpt-5': ModelPricing(Decimal('0.00125'), Decimal('0.010'), Provider.AZURE),
            'azure-gpt-5-mini': ModelPricing(Decimal('0.00025'), Decimal('0.002'), Provider.AZURE),
            'azure-gpt-5-nano': ModelPricing(Decimal('0.00005'), Decimal('0.0004'), Provider.AZURE),
            'azure-gpt-41': ModelPricing(Decimal('0.002'), Decimal('0.008'), Provider.AZURE),
            'azure-gpt-41-mini': ModelPricing(Decimal('0.0004'), Decimal('0.0016'), Provider.AZURE),
            'azure-gpt-4o': ModelPricing(Decimal('0.0025'), Decimal('0.010'), Provider.AZURE),
            'azure-gpt-4o-mini': ModelPricing(Decimal('0.00015'), Decimal('0.0006'), Provider.AZURE),
            'azure-o3': ModelPricing(Decimal('0.002'), Decimal('0.008'), Provider.AZURE),
            'azure-o4-mini': ModelPricing(Decimal('0.0011'), Decimal('0.0044'), Provider.AZURE),
            # Retired, retained for historical exports
            'azure-gpt-4': ModelPricing(Decimal('0.030'), Decimal('0.060'), Provider.AZURE),
            'azure-gpt-4-turbo': ModelPricing(Decimal('0.010'), Decimal('0.030'), Provider.AZURE),
            'azure-gpt-35-turbo': ModelPricing(Decimal('0.0005'), Decimal('0.0015'), Provider.AZURE),
        }

    def _validate_tokens(self, value, field_name: str, row_index: int) -> int:
        """
        Validate token count with strict error handling
        
        Args:
            value: Token count to validate
            field_name: Name of field (for error messages)
            row_index: Row number (for error messages)
            
        Returns:
            Validated integer token count
            
        Raises:
            ValueError: If token count is invalid
        """
        # Handle missing values
        if pd.isna(value):
            return 0
        
        # Convert to int (handles float strings like "100.0")
        try:
            tokens = int(float(value))
        except (ValueError, TypeError):
            logger.error(f"Row {row_index}: Invalid {field_name} = {value}")
            return 0  # Graceful degradation instead of crash
        
        # Validate range
        if tokens < 0:
            logger.error(f"Row {row_index}: Negative {field_name} = {tokens}")
            return 0  # Treat negative as 0
        
        # Sanity check (1M tokens ~= 750K words)
        if tokens > 1_000_000:
            logger.warning(
                f"Row {row_index}: Suspicious {field_name} = {tokens:,}. "
                f"Exceeds 1M tokens."
            )
        
        return tokens
    
    # Suffixes providers append to a model name that never change the price.
    _VERSION_SUFFIX = re.compile(
        r"-(?:latest|preview|\d{8}|\d{4}-\d{2}-\d{2}|\d{4})$"
    )

    def _normalize_model_name(self, model_name: str) -> str | None:
        """Map a reported model name onto a key in the pricing table.

        Matching is derived from the pricing table itself rather than a hardcoded
        list, and candidates are tried longest first so that a more specific model
        always wins. That ordering is the point: substring matching on shorter keys
        made "gpt-4o" resolve to "gpt-4" and bill it at twelve times its real rate.

        Examples:
            "gpt-4o-2024-08-06"        -> "gpt-4o"
            "gpt-4-0613"               -> "gpt-4"
            "GPT-4o"                   -> "gpt-4o"
            "claude-opus-5"            -> "claude-opus-5"
            "claude-3-opus-20240229"   -> "claude-3-opus"
            "gemini-2.5-pro-latest"    -> "gemini-2.5-pro"
            "azure-gpt-35-turbo-16k"   -> "azure-gpt-35-turbo"
        """
        if model_name in self.model_cache:
            return self.model_cache[model_name]

        if not model_name:
            return None

        model_lower = str(model_name).lower().strip()

        def remember(value: str) -> str:
            self.model_cache[model_name] = value
            return value

        # 1. Exact hit.
        if model_lower in self.pricing:
            return remember(model_lower)

        # 2. Drop a trailing date or version stamp and retry.
        stripped = self._VERSION_SUFFIX.sub("", model_lower)
        while stripped != model_lower:
            if stripped in self.pricing:
                return remember(stripped)
            model_lower, stripped = stripped, self._VERSION_SUFFIX.sub("", stripped)
        if stripped in self.pricing:
            return remember(stripped)

        # 3. Longest matching prefix in the pricing table. The boundary check keeps
        #    "gpt-4o" from being treated as a variant of "gpt-4".
        for key in sorted(self.pricing, key=len, reverse=True):
            if stripped == key or stripped.startswith(key + "-"):
                return remember(key)

        # 4. Azure deployments are frequently renamed by whoever created them, so
        #    fall back to matching the underlying OpenAI model inside the name.
        if "azure" in stripped:
            azure_keys = sorted(
                (k for k in self.pricing if k.startswith("azure-")), key=len, reverse=True
            )
            compact = stripped.replace("-", "").replace(".", "")
            for key in azure_keys:
                if key.replace("-", "").replace(".", "")[len("azure"):] in compact:
                    return remember(key)

        # Unrecognised. Returned as-is so the caller can flag it.
        return remember(stripped)

    def _detect_provider(self, model_name: str) -> Provider:
        """Detect provider with comprehensive pattern matching"""
        if not model_name:
            return Provider.UNKNOWN
        
        model_lower = str(model_name).lower().strip()
        
        # Azure first (may contain "gpt")
        if 'azure' in model_lower:
            return Provider.AZURE
        
        # OpenAI patterns
        openai_patterns = ['gpt-', 'gpt4', 'gpt3', 'gpt2', 'davinci', 'curie', 'babbage', 'ada', 'text-']
        if any(pattern in model_lower for pattern in openai_patterns):
            return Provider.OPENAI

        # Reasoning series: o1, o3, o4-mini and friends carry no 'gpt' prefix
        if re.fullmatch(r'o\d+(?:-(?:mini|pro|preview))*', model_lower):
            return Provider.OPENAI
        
        # Anthropic patterns
        if 'claude' in model_lower:
            return Provider.ANTHROPIC
        
        # Google patterns
        google_patterns = ['gemini', 'palm', 'bison']
        if any(pattern in model_lower for pattern in google_patterns):
            return Provider.GOOGLE
        
        return Provider.UNKNOWN
    
    def _get_model_pricing(self, model_name: str) -> tuple[ModelPricing, bool]:
        """
        Get pricing for model with unknown model tracking
        
        Returns:
            Tuple of (ModelPricing, is_known)
        """
        normalized = self._normalize_model_name(model_name)
        
        if normalized and normalized in self.pricing:
            return self.pricing[normalized], True
        
        # Track unknown model
        if model_name not in self.unknown_models:
            self.unknown_models.add(model_name)
            logger.warning(f"Unknown model: {model_name}. Cost set to $0.")
        
        # Return zero-cost pricing for unknown models
        provider = self._detect_provider(model_name)
        return ModelPricing(Decimal('0'), Decimal('0'), provider), False
    
    def _calculate_row_cost(
        self, 
        prompt_tokens: int, 
        completion_tokens: int, 
        pricing: ModelPricing
    ) -> Decimal:
        """
        Calculate cost for single API call with Decimal precision
        
        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            pricing: Model pricing data
            
        Returns:
            Cost in USD with 4 decimal places
        """
        input_cost = (Decimal(str(prompt_tokens)) * pricing.input_price) / Decimal('1000')
        output_cost = (Decimal(str(completion_tokens)) * pricing.output_price) / Decimal('1000')
        
        total_cost = input_cost + output_cost
        
        # Round to 4 decimal places (0.0001 = $0.01 per 100 calls)
        return total_cost.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names and auto-generate team column if missing"""
        # Column mapping
        column_mapping = {
            'model': None, 'prompt_tokens': None, 'completion_tokens': None,
            'prompt': None, 'system_prompt': None, 'team': None,
            'api_key': None, 'user_email': None, 'customer_id': None
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
                if column_mapping['team'] is None:
                    column_mapping['team'] = actual_col
            elif lower_col in ['api_key', 'apikey', 'key']:
                column_mapping['api_key'] = actual_col
            elif lower_col in ['user_email', 'email', 'user']:
                column_mapping['user_email'] = actual_col
            elif lower_col in ['customer_id', 'customerid', 'customer']:
                column_mapping['customer_id'] = actual_col
        
        # Rename columns
        rename_dict = {}
        for standard_name, actual_col in column_mapping.items():
            if actual_col and actual_col != standard_name:
                rename_dict[actual_col] = standard_name
        
        if rename_dict:
            df = df.rename(columns=rename_dict)
        
        # AUTO-GENERATE TEAM COLUMN IF MISSING
        if 'team' not in df.columns:
            if 'api_key' in df.columns:
                unique_keys = df['api_key'].unique()
                key_to_team = {key: f"Team-{chr(65+i)}" for i, key in enumerate(unique_keys[:26])}
                if len(unique_keys) > 26:
                    for i, key in enumerate(unique_keys[26:]):
                        key_to_team[key] = f"Team-{i+27}"
                df['team'] = df['api_key'].map(key_to_team)
                self.auto_generated_mapping = {'method': 'api_key', 'mapping': key_to_team}
                
            elif 'user_email' in df.columns:
                df['team'] = df['user_email'].apply(
                    lambda x: x.split('@')[0].split('.')[0].title() if pd.notna(x) and '@' in str(x) else 'Unknown'
                )
                self.auto_generated_mapping = {'method': 'email_domain', 'mapping': 'Generated from emails'}
                
            elif 'customer_id' in df.columns:
                df['team'] = df['customer_id'].apply(lambda x: f"Customer-{x}" if pd.notna(x) else 'Unknown')
                self.auto_generated_mapping = {'method': 'customer_id', 'mapping': 'Generated from customer IDs'}
                
            else:
                df['team'] = 'All Teams'
                self.auto_generated_mapping = {'method': 'default', 'mapping': 'All requests grouped together'}
        
        return df
    
    def analyze_usage(self, df: pd.DataFrame) -> dict:
        """Main analysis function with production-grade error handling"""
        
        # Normalize columns
        df = self._normalize_columns(df)
        
        # Validate required columns
        required_cols = ['model', 'prompt_tokens', 'completion_tokens']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            error_msg = f"""
ERROR: Missing required columns: {', '.join(missing_cols)}

REQUIRED COLUMNS:
- model (e.g., gpt-4, claude-3-opus, gemini-pro)
- prompt_tokens (input token count)
- completion_tokens (output token count)

YOUR COLUMNS: {', '.join(df.columns)}
            """
            return {
                'total_cost': 0, 'total_requests': 0, 'waste_identified': 0,
                'savings_potential': 0, 'patterns': [], 'recommendations': [],
                'team_breakdown': {}, 'error': error_msg.strip()
            }
        
        # Initialize results
        results = {
            'total_cost': 0, 'total_requests': len(df),
            'waste_identified': 0, 'savings_potential': 0,
            'patterns': [], 'recommendations': [],
            'team_breakdown': {}, 'provider_breakdown': {},
            'auto_generated_teams': self.auto_generated_mapping,
            'unknown_models': list(self.unknown_models)
        }
        
        # Add default columns
        if 'prompt' not in df.columns:
            df['prompt'] = 'N/A'
        if 'system_prompt' not in df.columns:
            df['system_prompt'] = ''
        
        # Calculate costs with validation
        total_cost = Decimal('0')
        team_costs = {}
        provider_costs = {}
        
        for idx, row in df.iterrows():
            # Validate tokens
            prompt_tokens = self._validate_tokens(row.get('prompt_tokens', 0), 'prompt_tokens', idx)
            completion_tokens = self._validate_tokens(row.get('completion_tokens', 0), 'completion_tokens', idx)
            
            # Get pricing
            model_name = row.get('model', '')
            pricing, is_known = self._get_model_pricing(model_name)
            
            # Calculate cost
            cost = self._calculate_row_cost(prompt_tokens, completion_tokens, pricing)
            total_cost += cost
            
            # Aggregate by team
            team = row.get('team', 'Unknown')
            team_costs[team] = team_costs.get(team, Decimal('0')) + cost
            
            # Aggregate by provider
            provider = pricing.provider.value
            if provider not in provider_costs:
                provider_costs[provider] = {'cost': Decimal('0'), 'requests': 0, 'tokens': 0}
            provider_costs[provider]['cost'] += cost
            provider_costs[provider]['requests'] += 1
            provider_costs[provider]['tokens'] += prompt_tokens + completion_tokens
        
        # Convert to float for JSON serialization
        results['total_cost'] = float(total_cost)
        results['team_breakdown'] = {k: float(v) for k, v in sorted(team_costs.items(), key=lambda x: x[1], reverse=True)}
        results['provider_breakdown'] = {
            k: {'cost': float(v['cost']), 'requests': v['requests'], 'tokens': v['tokens']}
            for k, v in sorted(provider_costs.items(), key=lambda x: x[1]['cost'], reverse=True)
        }
        
        # Run waste pattern detection
        # Note: These methods detect optimization opportunities
        # They use the full DataFrame with all data
        
        # Pattern 1: Duplicate prompts (can be cached)
        duplicate_waste = self._find_duplicate_prompts(df, total_cost)
        if duplicate_waste['waste_amount'] > 0:
            results['patterns'].append(duplicate_waste)
        
        # Pattern 2: Model overkill (expensive models for simple tasks)
        model_waste = self._find_model_overkill(df, total_cost)
        if model_waste['waste_amount'] > 0:
            results['patterns'].append(model_waste)
        
        # Calculate total waste and savings potential
        results['waste_identified'] = sum(float(p['waste_amount']) for p in results['patterns'])
        results['savings_potential'] = (results['waste_identified'] / results['total_cost'] * 100) if results['total_cost'] > 0 else 0
        
        # Add percentage to each pattern
        for pattern in results['patterns']:
            pattern['percentage'] = (pattern['waste_amount'] / results['total_cost'] * 100) if results['total_cost'] > 0 else 0
        
        # Generate recommendations based on patterns
        results['recommendations'] = self._generate_recommendations(results['patterns'])
        
        return results
    
    def _find_duplicate_prompts(self, df: pd.DataFrame, total_cost: Decimal) -> dict:
        """Find exact duplicate prompts that could be cached"""
        if 'prompt' not in df.columns or df['prompt'].isna().all():
            return {
                'name': 'Duplicate Prompts',
                'type': 'Duplicate Prompts',
                'waste_amount': 0.0,
                'percentage': 0,
                'fix': 'Implement exact prompt caching',
                'examples': [],
                'effort': 'LOW',
                'savings_range': '20-30%'
            }
        
        # Hash prompts to find duplicates
        prompt_groups = df.groupby(df['prompt'].apply(
            lambda x: hashlib.md5(str(x).encode()).hexdigest() if pd.notna(x) else 'na'
        ))
        
        waste = Decimal('0')
        examples = []
        
        for hash_val, group in prompt_groups:
            if len(group) > 1 and hash_val != 'na':
                group_waste = Decimal('0')
                # Calculate cost of duplicates (excluding first occurrence)
                for idx, row in group.iloc[1:].iterrows():
                    prompt_tokens = self._validate_tokens(row.get('prompt_tokens', 0), 'prompt_tokens', idx)
                    completion_tokens = self._validate_tokens(row.get('completion_tokens', 0), 'completion_tokens', idx)
                    pricing, _ = self._get_model_pricing(row.get('model', ''))
                    cost = self._calculate_row_cost(prompt_tokens, completion_tokens, pricing)
                    group_waste += cost
                waste += group_waste
                
                if group_waste > Decimal('0.01') and len(examples) < 3:
                    examples.append({
                        'prompt': str(group.iloc[0]['prompt'])[:100] + '...',
                        'count': len(group),
                        'waste': float(group_waste)
                    })
        
        return {
            'name': 'Duplicate Prompts',
            'type': 'Duplicate Prompts',
            'waste_amount': float(waste),
            'percentage': 0,
            'fix': 'Implement exact prompt caching (Redis/Memcached)',
            'examples': examples,
            'effort': 'LOW',
            'savings_range': '20-30%'
        }
    
    def _is_truly_simple_task(self, prompt: str, prompt_tokens: int, completion_tokens: int) -> bool:
        """
        Sophisticated heuristic to determine if a task is truly simple
        
        Uses word boundary matching to avoid false positives and includes
        multiple factors: keywords, prompt length, and output length.
        
        Args:
            prompt: The prompt text
            prompt_tokens: Input token count
            completion_tokens: Output token count
            
        Returns:
            True if task is simple, False if complex
        """
        import re
        
        prompt_lower = str(prompt).lower()
        
        # Exclude if contains complex task indicators (use word boundaries)
        for pattern in self.complex_task_patterns:
            # Create regex pattern with word boundaries
            regex_pattern = r'\b' + pattern.replace(' ', r'\s+') + r'\b'
            if re.search(regex_pattern, prompt_lower):
                return False
        
        # Exclude if prompt is very long (>500 tokens ~= 375 words)
        if prompt_tokens > 500:
            return False
        
        # Exclude if output is very long (>200 tokens suggests complex response)
        if completion_tokens > 200:
            return False
        
        # Check for simple task indicators (use word boundaries)
        has_simple_indicator = False
        for pattern in self.simple_task_patterns:
            regex_pattern = r'\b' + pattern.replace(' ', r'\s+') + r'\b'
            if re.search(regex_pattern, prompt_lower):
                has_simple_indicator = True
                break
        
        # Flag as simple if has indicator OR is very short (likely simple)
        is_very_short = prompt_tokens < 50 and completion_tokens < 50
        
        return has_simple_indicator or is_very_short
    
    def _find_model_overkill(self, df: pd.DataFrame, total_cost: Decimal) -> dict:
        """Find expensive model usage for simple tasks with sophisticated heuristics"""
        if 'prompt' not in df.columns or df['prompt'].isna().all():
            return {
                'name': 'Model Overkill',
                'type': 'Model Overkill',
                'waste_amount': 0.0,
                'percentage': 0,
                'fix': 'Route simple queries to cheaper models',
                'examples': [],
                'effort': 'LOW',
                'savings_range': '60-95%'
            }
        
        waste = Decimal('0')
        examples = []
        
        for idx, row in df.iterrows():
            model = str(row.get('model', '')).lower()
            prompt = str(row.get('prompt', ''))
            
            # Check if using expensive model
            is_expensive = any(x in model for x in ['gpt-4', 'claude-3-opus', 'claude-opus', 'gemini-1.5-pro'])
            
            if not is_expensive or prompt.lower() == 'n/a':
                continue
            
            # Get token counts
            prompt_tokens = self._validate_tokens(row.get('prompt_tokens', 0), 'prompt_tokens', idx)
            completion_tokens = self._validate_tokens(row.get('completion_tokens', 0), 'completion_tokens', idx)
            
            # Use sophisticated heuristic to check if truly simple
            is_simple = self._is_truly_simple_task(prompt, prompt_tokens, completion_tokens)
            
            if is_simple:
                # Get current cost
                current_pricing, _ = self._get_model_pricing(row.get('model', ''))
                current_cost = self._calculate_row_cost(prompt_tokens, completion_tokens, current_pricing)
                
                # Suggest cheaper alternative
                provider = self._detect_provider(model)
                if provider == Provider.OPENAI:
                    suggested_model = 'gpt-3.5-turbo'
                elif provider == Provider.ANTHROPIC:
                    suggested_model = 'claude-3-haiku'
                elif provider == Provider.GOOGLE:
                    suggested_model = 'gemini-1.5-flash'
                else:
                    suggested_model = 'gpt-3.5-turbo'
                
                # Calculate potential cost with cheaper model
                cheaper_pricing, _ = self._get_model_pricing(suggested_model)
                cheaper_cost = self._calculate_row_cost(prompt_tokens, completion_tokens, cheaper_pricing)
                
                savings = current_cost - cheaper_cost
                waste += savings
                
                if len(examples) < 3 and savings > Decimal('0.001'):
                    examples.append({
                        'prompt': prompt[:100] + '...',
                        'current_model': row.get('model', ''),
                        'suggested_model': suggested_model,
                        'savings': float(savings)
                    })
        
        return {
            'name': 'Model Overkill',
            'type': 'Model Overkill',
            'waste_amount': float(waste),
            'percentage': 0,
            'fix': 'Route simple queries to cheaper models',
            'examples': examples,
            'effort': 'LOW',
            'savings_range': '60-95%'
        }
    
    def _generate_recommendations(self, patterns: list[dict]) -> list[dict]:
        """Generate actionable recommendations based on patterns"""
        recommendations = []
        
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


# Retained for backwards compatibility. The class handles four providers and more than
# waste analysis, so the old name was misleading; prefer CostAnalyzer in new code.
OpenAIWasteAnalyzer = CostAnalyzer
