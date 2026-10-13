import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from database import SessionLocal
from sqlalchemy import select
from sqlalchemy.orm import Session
from pwdlib import PasswordHash
import jwt
from datetime import datetime, timedelta, timezone
import models
import schemas

password_hash = PasswordHash.recommended()

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

app = FastAPI()

@app.post("/tasks", response_model=schemas.TaskResponse)
def post_task(task: schemas.TaskCreate, db: Session=Depends(get_db), 
              current_user: models.User=Depends(get_current_user)):
    db_task = models.Task(
        title = task.title,
        description = task.description,
        completed = task.completed,
        user_id = current_user.id,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.get("/tasks", response_model=list[schemas.TaskResponse])
def get_tasks(db: Session=Depends(get_db), 
              current_user: models.User = Depends(get_current_user)):
    statement = select(models.Task).where(
        models.Task.user_id == current_user.id
    )
    result = db.scalars(statement).all()
    return result

@app.get("/tasks/{task_id}", response_model=schemas.TaskResponse)
def get_task(task_id: int, db: Session=Depends(get_db), 
             current_user: models.User = Depends(get_current_user)):
    statement = select(models.Task).where(
        models.Task.id == task_id,
        models.Task.user_id == current_user.id
    )
    result = db.scalar(statement)
    if result is not None:
        return result

    raise HTTPException(
        status_code=404,
        detail="Task not found"
    )

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session=Depends(get_db),
                current_user: models.User = Depends(get_current_user)):
    statement = select(models.Task).where(
        models.Task.id == task_id,
        models.Task.user_id == current_user.id
    )

    result = db.scalar(statement)
    if result is not None:
        db.delete(result)
        db.commit()
        return {"message": "Task deleted"}
    
    raise HTTPException(
        status_code=404,
        detail="Task not found"
    )

@app.patch("/tasks/{task_id}", response_model=schemas.TaskResponse)
def update_task(task_id: int, task_update: schemas.TaskUpdate, db: Session=Depends(get_db),
                current_user: models.User = Depends(get_current_user)):
    statement = select(models.Task).where(
        models.Task.id == task_id,
        models.Task.user_id == current_user.id
    )
    result = db.scalar(statement)
    if result is not None:
        updates = task_update.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(result, field, value)
        db.commit()
        db.refresh(result)
        return result
    
    raise HTTPException(
        status_code=404,
        detail="Task not found"
    )

@app.post("/users", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session=Depends(get_db)):
    db_user = models.User(
        username = user.username,
        hashed_password = password_hash.hash(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/login")
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