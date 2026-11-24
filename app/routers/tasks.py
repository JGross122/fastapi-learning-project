from fastapi import APIRouter

from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models as models
import app.schemas as schemas
from app.database import get_db
from app.auth import get_current_user, password_hash

router = APIRouter()

@router.post("/tasks", response_model=schemas.TaskResponse)
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

@router.get("/tasks", response_model=list[schemas.TaskResponse])
def get_tasks(db: Session=Depends(get_db), 
              current_user: models.User = Depends(get_current_user)):
    statement = select(models.Task).where(
        models.Task.user_id == current_user.id
    )
    result = db.scalars(statement).all()
    return result

@router.get("/tasks/{task_id}", response_model=schemas.TaskResponse)
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

@router.delete("/tasks/{task_id}")
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

@router.patch("/tasks/{task_id}", response_model=schemas.TaskResponse)
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