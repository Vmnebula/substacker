"""
OpenAI client wrapper that tracks API usage in real-time
"""

import time
import requests
from typing import Optional, Any
from datetime import datetime
import tiktoken


class SubstackerTracker:
    """Wrapper for OpenAI client that tracks usage"""
    
    def __init__(self, openai_client, api_key: str, team: str, endpoint: str = "https://substacker.nayacloud.com/api/track"):
        """
        Initialize tracker
        
        Args:
            openai_client: OpenAI client instance
            api_key: Substacker API key (sk_substacker_xxx)
            team: Team name for attribution
            endpoint: Substacker API endpoint (default: production)
        """
        self._client = openai_client
        self._substacker_key = api_key
        self._team = team
        self._endpoint = endpoint
        self._encoding = None
        
    def _get_encoding(self, model: str):
        """Get token encoding for model"""
        if self._encoding is None:
            try:
                self._encoding = tiktoken.encoding_for_model(model)
            except:
                self._encoding = tiktoken.get_encoding("cl100k_base")
        return self._encoding
    
    def _estimate_tokens(self, text: str, model: str) -> int:
        """Estimate token count for text"""
        try:
            encoding = self._get_encoding(model)
            return len(encoding.encode(text))
        except:
            # Fallback: rough estimate (1 token ~= 4 chars)
            return len(text) // 4
    
    def _track_usage(self, model: str, prompt_tokens: int, completion_tokens: int, response_time: float):
        """Send usage data to Substacker API"""
        try:
            payload = {
                # Keep api_key in payload for backwards compatibility but also send as header
                "api_key": self._substacker_key,
                "team": self._team,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "response_time": response_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to Substacker API (async, don't block on failure)
            headers = {"X-API-Key": self._substacker_key}
            response = requests.post(
                self._endpoint,
                json=payload,
                headers=headers,
                timeout=2  # Quick timeout - don't slow down user's app
            )
            
            if response.status_code != 200:
                print(f"Substacker tracking warning: {response.status_code}")
                
        except Exception as e:
            # Silently fail - don't break user's app if tracking fails
            print(f"Substacker tracking error: {e}")
    
    def __getattr__(self, name):
        """Proxy all attributes to underlying OpenAI client"""
        return getattr(self._client, name)


class ChatCompletionsProxy:
    """Proxy for chat.completions that tracks usage"""
    
    def __init__(self, original_completions, tracker):
        self._original = original_completions
        self._tracker = tracker
    
    def create(self, *args, **kwargs):
        """Intercept create() calls to track usage"""
        model = kwargs.get('model', 'gpt-3.5-turbo')
        start_time = time.time()
        
        # Make actual OpenAI API call
        response = self._original.create(*args, **kwargs)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Extract token usage from response
        if hasattr(response, 'usage') and response.usage:
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
        else:
            # Fallback: estimate tokens if not in response
            messages = kwargs.get('messages', [])
            prompt_text = ' '.join([m.get('content', '') for m in messages if isinstance(m, dict)])
            prompt_tokens = self._tracker._estimate_tokens(prompt_text, model)
            
            completion_text = ''
            if hasattr(response, 'choices') and response.choices:
                completion_text = response.choices[0].message.content if hasattr(response.choices[0].message, 'content') else ''
            completion_tokens = self._tracker._estimate_tokens(completion_text, model)
        
        # Track usage asynchronously
        self._tracker._track_usage(model, prompt_tokens, completion_tokens, response_time)
        
        return response
    
    def __getattr__(self, name):
        """Proxy other attributes"""
        return getattr(self._original, name)


class ChatProxy:
    """Proxy for chat object"""
    
    def __init__(self, original_chat, tracker):
        self._original = original_chat
        self._tracker = tracker
        self.completions = ChatCompletionsProxy(original_chat.completions, tracker)
    
    def __getattr__(self, name):
        """Proxy other attributes"""
        return getattr(self._original, name)


def track_openai(openai_client, api_key: str, team: str, endpoint: str = "https://substacker.nayacloud.com/api/track"):
    """
    Wrap OpenAI client to track API usage in real-time
    
    Usage:
        from openai import OpenAI
        from substacker import track_openai
        
        openai = track_openai(
            OpenAI(),
            api_key="sk_substacker_xxx",
            team="engineering"
        )
        
        # Use OpenAI normally - tracking happens automatically
        response = openai.chat.completions.create(...)
    
    Args:
        openai_client: OpenAI client instance
        api_key: Your Substacker API key (get from dashboard)
        team: Team name for cost attribution (e.g., "engineering", "marketing")
        endpoint: Substacker API endpoint (default: production)
    
    Returns:
        Wrapped OpenAI client with tracking enabled
    """
    tracker = SubstackerTracker(openai_client, api_key, team, endpoint)
    
    # Wrap the chat.completions object to intercept create() calls
    if hasattr(openai_client, 'chat'):
        tracker.chat = ChatProxy(openai_client.chat, tracker)
    
    return tracker
