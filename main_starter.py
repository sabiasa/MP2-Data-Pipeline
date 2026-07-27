import secrets

from fastapi import FastAPI, HTTPException, Header, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from db import get_articles, get_article_by_id, count_articles
import hmac
from pydantic_settings import BaseSettings, SettingsConfigDict
import jwt as pyjwt
HAS_JWT = True



# 1. CONFIG — Baca dari .env
class Settings(BaseSettings):
    database_url: str
    internal_api_key: str
    jwt_secret: str
    jwt_expiry_minutes: int = 30
    client_id: str
    client_secret: str

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )

settings = Settings()

app = FastAPI(
    title="News Pipeline API",
    description="End-to-End Data Pipeline — Session 10",
    version="1.0"
)

security_scheme = HTTPBearer(auto_error=False)

# Pydantic
class Article(BaseModel):
    id: int
    title: str
    url: str
    source: str
    content: Optional[str] = None
    published_at: Optional[datetime] = None
    scraped_at: Optional[datetime] = None

class TokenRequest(BaseModel):
    """Request body untuk endpoint /token"""
    client_id: str
    client_secret: str

class TokenResponse(BaseModel):
    """Response dari endpoint /token"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# Metode Security Access token (client-id, client secret)
def create_access_token(client_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": client_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expiry_minutes),
        "jti": secrets.token_hex(16)  
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm="HS256")

def verify_jwt_token(token: str) -> dict:
   try:
    return pyjwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
   except pyjwt.ExpiredSignatureError:
    raise HTTPException(status_code=401, detail="Token expired")
   except pyjwt.InvalidTokenError:
    raise HTTPException(status_code=401, detail="Invalid token")

# Metode API Key
def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if x_api_key is None:
        return None
    if hmac.compare_digest(x_api_key, settings.internal_api_key):
        return {"auth_method": "api_key"}
    raise HTTPException(status_code=401, detail="Unauthorized")
    
def get_current_client(
    api_key_result=Depends(verify_api_key),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
):
    if api_key_result is not None:
        return api_key_result
    if credentials is not None:
        payload = verify_jwt_token(credentials.credentials)
        return {"auth_method": "bearer", "client_id": payload["sub"]}
    raise HTTPException(status_code=401, detail="Not authenticated, use authenticated key or bearer token", headers= {"WWW-Authenticate": "Bearer"})

# Start Route
@app.get("/", tags=["Public"])
def read_root():
    return {"message": "News Pipeline API — Session 10"}

@app.get("/check_status", tags=["Public"])
def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/token", response_model=TokenResponse, tags=["Auth"])
def login_for_token(req: TokenRequest):
    valid_id = hmac.compare_digest(req.client_id, settings.client_id)
    valid_secret = hmac.compare_digest(req.client_secret, settings.client_secret)
    if not (valid_id and valid_secret):
        raise HTTPException(status_code=401, detail="Invalid client credentials")
    token = create_access_token(req.client_id)
    return TokenResponse(
        access_token=token, 
        token_type="bearer",
        expires_in=settings.jwt_expiry_minutes * 60
    )

# Protected Endpoint
@app.get("/articles", response_model=List[Article], tags=["Articles"])
def list_articles(
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(20, le=100, description="Max 100 articles"),
    auth=Depends(get_current_client),
):
    return get_articles(source=source, limit=limit)


@app.get("/articles/{article_id}", response_model=Article, tags=["Articles"])
def get_article(
    article_id: int,
    auth=Depends(get_current_client),
):
    article = get_article_by_id(article_id)
    if not article: #jika gaada id nya dalam tabel artikel 
        raise HTTPException(status_code=404, detail="Article not found")
    return article

# Buat endpoint artivles meneima query  parameter 1, source, 2 title, 3 limit

# Buat endpoint untuk mendapatkan total article 