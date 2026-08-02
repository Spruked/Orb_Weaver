"""Security layer — owner authentication"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In production, these come from a vault. Here we seed one owner.
OWNER_STORE = {
    "owner@orb.system": {
        "hashed_password": pwd_context.hash("orb-owner-2026"),
        "role": "owner",
        "name": "ORB Owner"
    }
}

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def authenticate_owner(email: str, password: str) -> Optional[dict]:
    user = OWNER_STORE.get(email)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return {"email": email, "role": user["role"], "name": user["name"]}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None
