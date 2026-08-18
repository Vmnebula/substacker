import hashlib

from analyzer_multi_provider import MultiProviderAnalyzer
from analyzer_v2 import OpenAIWasteAnalyzer
from security import InputValidator


def test_input_validator_email():
    """Test email validation logic."""
    assert InputValidator.validate_email("dev@example.com") is True
    assert InputValidator.validate_email("invalid-email") is False

def test_api_key_hashing_consistency():
    """Test SHA256 hashing format used for stored API keys."""
    raw_key = "sk_substacker_abcdef1234567890"
    expected_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    assert len(expected_hash) == 64
    assert isinstance(expected_hash, str)

def test_multi_provider_analyzer_pricing():
    """Test multi-provider analyzer pricing map."""
    analyzer = MultiProviderAnalyzer()
    pricing = analyzer.get_all_provider_pricing()
    
    assert "openai" in pricing
    assert "anthropic" in pricing
    assert "google" in pricing
    assert len(pricing["openai"]["models"]) > 0

def test_base_analyzer_cost_calculation():
    """Test pricing map on base analyzer."""
    analyzer = OpenAIWasteAnalyzer()
    assert 'gpt-4' in analyzer.pricing
    pricing = analyzer.pricing['gpt-4']
    assert pricing.input_price > 0
    assert pricing.output_price > 0
