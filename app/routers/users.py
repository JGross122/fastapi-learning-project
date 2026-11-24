from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models as models
import app.schemas as schemas
from app.database import get_db
from app.auth import password_hash, create_access_token

router = APIRouter()

@router.post("/users", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session=Depends(get_db)):
    db_user = models.User(
        username = user.username,
        hashed_password = password_hash.hash(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    statement = select(models.User).where(
        models.User.username == form_data.username
    )

    db_user = db.scalar(statement)

    if db_user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )
 
    is_verified = password_hash.verify(
        form_data.password,
        db_user.hashed_password
    )

    if not is_verified:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    access_token = create_access_token(db_user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }