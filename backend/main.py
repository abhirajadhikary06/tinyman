from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from jose import jwt, JWTError
import os

from .auth import router as auth_router, oauth_complete_router
from .config import PROXY_CLASS_CODE
from .cache import cache
from .tinyfish import scrape_url
from .fireworks import generate_code
from .usage import get_usage_payload, record_tinyfish_usage, record_fireworks_usage

app = FastAPI(title="tinyman", version="1.0.0")

app.include_router(auth_router)
app.include_router(oauth_complete_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

security = HTTPBearer()

async def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(cred.credentials, os.getenv("JWT_SECRET_KEY"), algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

class SynthesizePayload(BaseModel):
    target_url: str
    force_regenerate: bool = False

@app.get("/")
async def root():
    return FileResponse("frontend/auth.html")

@app.get("/auth")
async def auth_page():
    return FileResponse("frontend/auth.html")

@app.get("/main")
async def main_page():
    return FileResponse("frontend/main.html")

@app.get("/output")
async def output_page():
    return FileResponse("frontend/output.html")

@app.get("/usage")
async def usage_page():
    return FileResponse("frontend/usage.html")

@app.get("/api/v1/usage")
async def usage_dashboard_data(user=Depends(get_current_user)):
    return get_usage_payload()

@app.post("/api/v1/synthesize")
async def synthesize(payload: SynthesizePayload, user=Depends(get_current_user)):
    url = payload.target_url.strip()
    cache_key = url

    if not payload.force_regenerate:
        cached = cache.get(cache_key)
        if cached:
            return {"status": "success", "code": cached, "cached": True}

    # Non-API website mode only
    record_tinyfish_usage()
    scraped = await scrape_url(
        url,
        "Analyze publicly accessible pages and flows to identify safe automation targets (forms, listing pages, pagination, filters) and data fields.",
        is_docs=False,
    )
    llm_prompt = f"""
Generate a compact, accurate Python website SDK for {url} using only legitimate public web interactions.

Public page analysis:
{scraped}

Requirements:
- Class name: Web{url.split('//')[-1].split('.')[0].title().replace('-','')}SDK
- MUST include the exact CredentialProxy class below
- Use only public endpoints/pages and standard requests-based interactions
- Do NOT use intercepted/private/internal endpoints
- Do NOT use stolen/session tokens or bypass auth
- All HTTP calls MUST use self.proxy.make_request(...)
- Keep code concise and readable (target 90-170 lines total)
- Provide practical methods: fetch_page, search, list_items, parse_items, get_item_detail, paginate
- IMPORTANT: Do not hardcode paths like /products unless clearly present in analysis
- Add a listing_path argument with safe fallback to '/' when uncertain
- Add resilient selectors with multiple fallbacks and return [] when no items are found
- For BeautifulSoup/SoupSieve selectors, NEVER use deprecated :contains; use :-soup-contains('text')
- Handle absolute/relative URLs correctly with urljoin
- parse_items must accept html string; fetch_page/search/list_items should return Response
- Include basic request timeout, raise_for_status, and predictable return shapes
- No markdown, no explanations, code only

{PROXY_CLASS_CODE}

Output ONLY the full Python code.
"""

    record_fireworks_usage()
    code = await generate_code(llm_prompt)
    cache.set(cache_key, code)

    return {"status": "success", "code": code, "cached": False}