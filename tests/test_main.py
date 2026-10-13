import os
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from main import app, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models
import pytest

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]
test_engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit = False
)

models.Base.metadata.create_all(bind=test_engine)

@pytest.fixture(autouse=True)
def reset_database():
    models.Base.metadata.drop_all(bind=test_engine)
    models.Base.metadata.create_all(bind=test_engine)

@pytest.fixture()
def test_user():
    credentials = {
            "username": "testusername",
            "password": "testpassword"
    }
    response = client.post(
        "/users",
        json = credentials
    )

    assert response.status_code == 200
    
    return credentials

@pytest.fixture()
def auth_headers(test_user):
    response = client.post(
        "/login",
        data=test_user
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_get_tasks_without_login():
    response = client.get("/tasks")

    assert response.status_code == 401

def test_create_user():
    response = client.post(
        "/users",
        json = {
            "username": "testuser",
            "password": "testpassword"
        }
    )
    assert response.status_code==200

def test_login():
    client.post(
        "/users",
        json={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    response = client.post(
        "/login",
        data = {
            "username": "testuser",
            "password": "testpassword"
        }
    )

    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password():
    client.post(
        "/users",
        json={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    response = client.post(
        "/login",
        data={
            "username": "testuser",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401

def test_login_unknown_user():
    response = client.post(
        "/login",
        data = {
            "username": "ghostuser",
            "password": "12345678"
        }
    )
    assert response.status_code == 401

def test_authenticated_user_can_create_task(auth_headers):
    response = client.post(
        "/tasks",
        json = {
            "title": "tasktitle",
            "description": "taskdescription",
            "completed": False
        },
        headers = auth_headers
    )
    assert response.status_code == 200
    assert response.json()["title"] == "tasktitle"

def test_unauthenticated_user_create_task():
    response = client.post(
        "/tasks",
         json = {
            "title": "tasktitle",
            "description": "taskdescription",
            "completed": False
        }
    )
    assert response.status_code == 401

def test_authenticated_user_can_get_own_tasks(auth_headers):
    client.post(
        "/tasks",
        json = {
            "title": "tasktitle",
            "description": "taskdescription",
            "completed": False
        },
        headers = auth_headers
    )
    response = client.get(
        "/tasks",
        headers = auth_headers
    )

    assert response.status_code == 200

    assert response.json()[0]["title"] == "tasktitle"

    assert len(response.json()) == 1

def test_user_cant_get_someones_task(auth_headers):
    response_create_task = client.post(
        "/tasks",
        json = {
            "title": "tasktitle",
            "description": "taskdescription",
            "completed": False
        },
        headers = auth_headers
    )
    response_create_second_user = client.post(
        "/users",
        json={
            "username": "seconduser",
            "password": "testpassword"
        }
    )
    reponse_login_second_user = client.post(
        "/login",
        data={
            "username": "seconduser",
            "password": "testpassword"
        }
    )

    second_user_accesstoken = reponse_login_second_user.json()["access_token"]

    task_id = response_create_task.json()["id"]

    response_get_task_wrong_user = client.get(
        f"/tasks/{task_id}",
        headers={"Authorization": f"Bearer {second_user_accesstoken}"}
    )   
    assert response_get_task_wrong_user.status_code == 404

def test_authenticated_user_can_update_task(auth_headers):
    response_create_task = client.post(
        "/tasks", 
        json = {
            "title": "tasktitle",
            "description": "taskdescription",
            "completed": False
        },
        headers = auth_headers
    )

    task_id = response_create_task.json()["id"]

    response_update_task = client.patch(
        f"/tasks/{task_id}",
        json = {
            "title": "updatedtitle"
        },
        headers = auth_headers
    )

    assert response_update_task.status_code == 200

    response_get_task = client.get(
        f"/tasks/{task_id}",
        headers = auth_headers
    )

    assert response_get_task.json()["title"] == "updatedtitle"

    assert response_get_task.status_code == 200

    assert response_get_task.json()["description"] == "taskdescription"


def test_authenticated_user_can_delete_task(auth_headers):
    response_create_task = client.post(
         "/tasks", 
        json = {
            "title": "tasktitle",
            "description": "taskdescription",
            "completed": False
        },
        headers = auth_headers
    )

    task_id = response_create_task.json()["id"]

    response_delete_task = client.delete(
        f"/tasks/{task_id}",
        headers = auth_headers
    )

    assert response_delete_task.status_code == 200

    response_get_task = client.get(
        f"/tasks/{task_id}",
        headers = auth_headers
    )

    assert response_get_task.status_code == 404

