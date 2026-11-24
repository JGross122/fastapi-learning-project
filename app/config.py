import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
EXPIRATION_MINUTES = 30