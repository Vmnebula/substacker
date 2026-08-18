# Substacker SDK

Python client for [Substacker](https://github.com/Vmnebula/substacker). It wraps an
existing OpenAI client and reports token usage and cost for team-level attribution.

## Installation

The SDK is not published to PyPI yet. Install it from the repository:

```bash
pip install "git+https://github.com/Vmnebula/substacker.git#subdirectory=substacker_sdk"
```

Or from a local checkout:

```bash
pip install ./substacker_sdk
```

## Usage

```python
from openai import OpenAI

from substacker_sdk import track_openai

client = track_openai(
    OpenAI(),
    api_key="sk_substacker_...",
    team="engineering",
    endpoint="http://localhost:8000/api/track",
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}],
)
```

The wrapper proxies every attribute to the underlying client, so existing code
continues to work unchanged.

## Arguments

| Argument | Required | Default | Description |
| --- | --- | --- | --- |
| `openai_client` | yes | | An instantiated `openai.OpenAI` client. |
| `api_key` | yes | | Substacker API key, issued from the admin dashboard. |
| `team` | yes | | Team name that usage is attributed to. |
| `endpoint` | no | `http://localhost:8000/api/track` | URL of the Substacker tracking endpoint. |

## Behaviour

- **Reporting does not block your request.** Usage is handed to a background worker
  thread; the calling thread returns as soon as the OpenAI response does.
- **Tracking failures never propagate.** If the collector is unreachable or returns an
  error, the SDK logs a warning through the `substacker_sdk.tracker` logger and your
  application continues normally.
- **Token counts** come from the OpenAI response when available, and fall back to a
  `tiktoken` estimate otherwise.

To see reporting failures during development, enable logging:

```python
import logging

logging.basicConfig(level=logging.WARNING)
```

## Requirements

- Python 3.9 or newer
- `openai` 1.0 or newer
- A running Substacker instance to report to

## License

MIT. See the [repository LICENSE](https://github.com/Vmnebula/substacker/blob/main/LICENSE).
