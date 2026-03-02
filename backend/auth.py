from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
import os
from datetime import datetime, timedelta
from jose import jwt
from dotenv import load_dotenv

router = APIRouter(prefix="/auth", tags=["auth"])
oauth_complete_router = APIRouter(prefix="/oauth/complete", tags=["auth"])

load_dotenv()

PROVIDERS = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "scope": "openid email profile",
        "redirect_uri": "http://localhost:8000/auth/google/callback"
    },
    "github": {
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "user_url": "https://api.github.com/user",
        "client_id": os.getenv("GITHUB_CLIENT_ID"),
        "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
        "scope": "user:email",
        "redirect_uri": "http://localhost:8000/auth/github/callback"
    },
    "gitlab": {
        "auth_url": "https://gitlab.com/oauth/authorize",
        "token_url": "https://gitlab.com/oauth/token",
        "user_url": "https://gitlab.com/api/v4/user",
        "client_id": os.getenv("GITLAB_CLIENT_ID"),
        "client_secret": os.getenv("GITLAB_CLIENT_SECRET"),
        "scope": "read_user",
        "redirect_uri": "http://localhost:8000/auth/gitlab/callback"
    }
}

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

async def exchange_code(provider: str, code: str):
    p = PROVIDERS[provider]
    async with httpx.AsyncClient() as c:
        data = {
            "client_id": p["client_id"],
            "client_secret": p["client_secret"],
            "code": code,
            "redirect_uri": p["redirect_uri"],
            "grant_type": "authorization_code",
        }
        headers = {"Accept": "application/json"}
        r = await c.post(p["token_url"], data=data, headers=headers)
        r.raise_for_status()
        return r.json()

async def fetch_user(provider: str, token: str):
    p = PROVIDERS[provider]
    async with httpx.AsyncClient() as c:
        headers = {"Authorization": f"Bearer {token}" if provider != "github" else f"token {token}"}
        r = await c.get(p["user_url"], headers=headers)
        r.raise_for_status()
        return r.json()

def create_jwt(user: dict) -> str:
    expire = datetime.utcnow() + timedelta(hours=24)
    payload = {
        "sub": str(user.get("id") or user.get("sub")),
        "email": user.get("email"),
        "name": user.get("name"),
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

@router.get("/{provider}")
async def login(provider: str):
    if provider not in PROVIDERS:
        raise HTTPException(400, "Invalid provider")
    p = PROVIDERS[provider]
    auth_url = f"{p['auth_url']}?client_id={p['client_id']}&redirect_uri={p['redirect_uri']}&response_type=code&scope={p['scope'].replace(' ', '+')}"
    return RedirectResponse(auth_url)

@router.get("/{provider}/callback")
async def callback(provider: str, code: str):
    if provider not in PROVIDERS:
        raise HTTPException(400)
    try:
        token_data = await exchange_code(provider, code)
        access_token = token_data.get("access_token") or token_data.get("token")
        user_info = await fetch_user(provider, access_token)
        jwt_token = create_jwt(user_info)

        html = f"""
        <!DOCTYPE html>
        <html><head><title>Login Success - tinyman</title></head>
        <body>
            <script>
                localStorage.setItem('jwt_token', '{jwt_token}');
                window.location.href = '/main';
            </script>
        </body></html>
        """
        return HTMLResponse(html)
    except Exception as e:
        raise HTTPException(400, f"OAuth failed: {str(e)}")


@oauth_complete_router.get("/{provider}/")
async def callback_oauth_complete(provider: str, code: str):
    return await callback(provider, code)


@oauth_complete_router.get("/{provider}")
async def callback_oauth_complete_no_slash(provider: str, code: str):
    return await callback(provider, code)