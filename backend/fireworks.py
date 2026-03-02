import os
import httpx


FIREWORKS_URL = "https://api.fireworks.ai/inference/v1/chat/completions"
FIREWORKS_MODEL = "accounts/fireworks/models/deepseek-v3p1"


def _clean_code_block(content: str) -> str:
    code = content.strip()
    if code.startswith("```python"):
        return code.split("```python", 1)[1].split("```", 1)[0].strip()
    if code.startswith("```"):
        return code.split("```", 2)[1].strip()
    return code


async def generate_code(prompt: str) -> str:
    """Generate production-grade SDK with Fireworks.ai chat completions API."""
    api_key = os.getenv("FIREWORKS_API_KEY")
    if not api_key:
        return "# Fireworks generation failed: FIREWORKS_API_KEY is not set"

    payload = {
        "model": FIREWORKS_MODEL,
        "max_tokens": 4096,
        "top_p": 1,
        "top_k": 40,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "temperature": 0.6,
        "messages": [
            {
                "role": "system",
                "content": "You are a Principal Python Backend Engineer. Output ONLY clean, concise, production-ready Python code. Favor small practical SDKs over boilerplate. Use modern BeautifulSoup/SoupSieve selectors only: never use deprecated :contains, use :-soup-contains('text') instead. No explanations, no markdown fences.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(FIREWORKS_URL, headers=headers, json=payload)
            response.raise_for_status()

        body = response.json()
        code = (
            body.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not code:
            return "# Fireworks generation failed: empty completion content"

        return _clean_code_block(code)
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:500]
        return f"# Fireworks generation failed: {e.response.status_code} {detail}"
    except Exception as e:
        return f"# Fireworks generation failed: {str(e)}\n# Try again or check your FIREWORKS_API_KEY"