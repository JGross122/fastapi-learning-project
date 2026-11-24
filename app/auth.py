import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
import app.models as models

password_hash = PasswordHash.recommended()

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def create_access_token(user_id: int):
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30) # 30 minutes token lifetime
    payload = {
        "sub":str(user_id),
        "exp":expires_at
    }
    encoded_jwt = jwt.encode(
        payload=payload,
        key=JWT_SECRET_KEY,
        algorithm=ALGORITHM
    )
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    statement = select(models.User).where(
        models.User.id == user_id
    )
    db_user = db.scalar(statement)

    if db_user is not None:
        return db_user

    raise HTTPException(
        status_code=401,
        detail="Invalid credentials"
    )

