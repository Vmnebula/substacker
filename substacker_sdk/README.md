# Substacker SDK - Real-Time AI Cost Tracking

Track your OpenAI API costs in real-time with team attribution.

## Installation

```bash
pip install substacker-sdk
```

## Quick Start

```python
from openai import OpenAI
from substacker import track_openai

# Wrap your OpenAI client
openai = track_openai(
    OpenAI(),
    api_key="sk_substacker_xxx",  # Get from substacker.nayacloud.com
    team="engineering"             # Your team name
)

# Use OpenAI normally - tracking happens automatically
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)

# That's it! Usage is tracked in real-time on your Substacker dashboard
```

## How It Works

1. The SDK wraps your OpenAI client
2. Intercepts all API calls transparently
3. Sends usage data to Substacker API
4. Your dashboard updates in real-time
5. Your code continues working exactly as before

## Features

-  **Zero latency impact** - Tracking happens asynchronously
-  **Fail-safe** - If tracking fails, your app continues working
-  **Team attribution** - Specify team name for cost breakdown
-  **Real-time dashboard** - See costs update live
-  **No code changes** - Just wrap the client once

## Get Your API Key

1. Sign up at [substacker.nayacloud.com](https://substacker.nayacloud.com)
2. Go to Settings → API Keys
3. Copy your `sk_substacker_xxx` key
4. Use it in the `track_openai()` call

## Local Development

For local testing, point to localhost:

```python
openai = track_openai(
    OpenAI(),
    api_key="sk_substacker_xxx",
    team="engineering",
    endpoint="http://localhost:8000/api/track"  # Local endpoint
)
```

## Examples

### Multiple Teams

```python
# Engineering team client
eng_client = track_openai(OpenAI(), api_key="sk_xxx", team="engineering")

# Marketing team client  
marketing_client = track_openai(OpenAI(), api_key="sk_xxx", team="marketing")

# Each tracks to their respective team in the dashboard
```

### Different Projects

```python
# Project A
client_a = track_openai(OpenAI(), api_key="sk_xxx", team="project-a")

# Project B
client_b = track_openai(OpenAI(), api_key="sk_xxx", team="project-b")
```

## Requirements

- Python 3.8+
- OpenAI SDK 1.0+
- Active Substacker account

## Support

- Documentation: [docs.substacker.nayacloud.com](https://docs.substacker.nayacloud.com)
- Issues: [github.com/substacker/sdk/issues](https://github.com/substacker/sdk/issues)
- Email: hello@substacker.nayacloud.com

## License

MIT
