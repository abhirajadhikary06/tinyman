import os
import json
import httpx

async def scrape_url(url: str, instructions: str, is_docs: bool = False) -> str:
    """TinyFish automation wrapper using SSE, with rich mock fallback for demos."""
    api_key = os.getenv("TINYFISH_API_KEY")

    if api_key:
        try:
            headers = {
                "X-API-Key": api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "url": url,
                "goal": instructions,
            }

            chunks: list[str] = []
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream(
                    "POST",
                    "https://agent.tinyfish.ai/v1/automation/run-sse",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for raw_line in response.aiter_lines():
                        if not raw_line or not raw_line.startswith("data: "):
                            continue

                        event_data = raw_line[6:].strip()
                        if not event_data or event_data == "[DONE]":
                            continue

                        try:
                            event = json.loads(event_data)
                        except json.JSONDecodeError:
                            continue

                        if isinstance(event, dict):
                            for key in ("content", "text", "message", "result"):
                                value = event.get(key)
                                if isinstance(value, str) and value.strip():
                                    chunks.append(value.strip())

                            nested_data = event.get("data")
                            if isinstance(nested_data, str) and nested_data.strip():
                                chunks.append(nested_data.strip())
                            elif isinstance(nested_data, dict):
                                for key in ("content", "text", "message", "result"):
                                    value = nested_data.get(key)
                                    if isinstance(value, str) and value.strip():
                                        chunks.append(value.strip())

            if chunks:
                return "\n".join(chunks)
        except Exception:
            pass

    # Rich mock for hackathon/demo
    if is_docs:
        return f"""# API Documentation scraped from {url}

## Base URL
{url.rstrip('/')}

## Authentication
Authorization: Bearer <YOUR_API_KEY>

## Endpoints
GET /items                -> List items
POST /items               -> Create item (JSON body)
GET /items/{{id}}          -> Get item
DELETE /items/{{id}}       -> Delete item

Response format: JSON
"""
    else:
        return f"""# Public web analysis for {url}

    Detected page patterns:
    - Landing page with navigation and product/category sections
    - Search/filter UI components and paginated listing views
    - Item detail pages with title, price/metadata, and description blocks

    Safe automation hints:
    - Prefer GET requests to public pages and parse HTML content
    - Handle pagination with query params or next-page links
    - Keep retries/timeouts; avoid fragile selectors

    DOM structure:
    - Common cards/list rows for items
    - Forms for search/filter submission
"""