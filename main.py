# from fastapi import Depends, FastAPI, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# from pydantic import BaseModel
# from datetime import datetime, timedelta
# from jose import JWTError, jwt
# from passlib.context import CryptContext
# from typing import Optional
# import os
# from dotenv import load_dotenv
# import mysql.connector
# from fastapi.middleware.cors import CORSMiddleware
# # from chat_websocket import router as chat_router
# from chat.websocket import router as chat_ws_router
# from db import get_db_connection, init_db_schema

# # Load environment variables
# load_dotenv()
# init_db_schema()

# # Validate required environment variables
# required_env_vars = [
#     "SECRET_KEY", "ALGORITHM", "ACCESS_TOKEN_EXPIRE_MINUTES",
#     "DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"
# ]
# missing_vars = [var for var in required_env_vars if not os.getenv(var)]
# if missing_vars:
#     raise RuntimeError(f"Missing required environment variables: {', '.join(missing_vars)}")

# # JWT configuration
# SECRET_KEY = os.getenv("SECRET_KEY")
# ALGORITHM = os.getenv("ALGORITHM")
# ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

# # Database configuration
# DB_HOST = os.getenv("DB_HOST")
# DB_USER = os.getenv("DB_USER")
# DB_PASSWORD = os.getenv("DB_PASSWORD")
# DB_NAME = os.getenv("DB_NAME")

# # FastAPI app and security
# app = FastAPI()
# app.include_router(chat_ws_router)
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# origins = [
#     "http://localhost:3000",  # local
#     "https://coinconnect.vercel.app",  # production
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Pydantic models
# class User(BaseModel):
#     username: str
#     email: str
#     password: str

# class Token(BaseModel):
#     access_token: str
#     token_type: str

# class TokenData(BaseModel):
#     email: Optional[str] = None


# def verify_password(plain_password, hashed_password):
#     return pwd_context.verify(plain_password, hashed_password)

# def get_password_hash(password):
#     return pwd_context.hash(password)

# def get_user_by_email(email: str):
#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)
#     cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
#     user = cursor.fetchone()
#     cursor.close()
#     conn.close()
#     return user

# def authenticate_user(email: str, password: str):
#     user = get_user_by_email(email)
#     if not user or not verify_password(password, user['hashed_password']):
#         return False
#     return user

# def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# async def get_current_user(token: str = Depends(oauth2_scheme)):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         email: str = payload.get("sub")
#         if not email:
#             raise credentials_exception
#         token_data = TokenData(email=email)
#     except JWTError:
#         raise credentials_exception

#     user = get_user_by_email(email=token_data.email)
#     if not user:
#         raise credentials_exception
#     return user

# async def get_current_active_user(current_user: dict = Depends(get_current_user)):
#     if current_user.get('disabled'):
#         raise HTTPException(status_code=400, detail="Inactive user")
#     return current_user

# # Routes
# @app.get("/")
# def home():
#     return "WELCOME HERE!"

# @app.post("/register", status_code=status.HTTP_201_CREATED)
# async def register_user(user: User):
#     conn = get_db_connection()
#     cursor = conn.cursor()
#     hashed_password = get_password_hash(user.password)
#     try:
#         cursor.execute(
#             "INSERT INTO users (username, email, hashed_password) VALUES (%s, %s, %s)",
#             (user.username, user.email, hashed_password)
#         )
#         conn.commit()
#     except mysql.connector.IntegrityError:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Username or email already exists"
#         )
#     finally:
#         cursor.close()
#         conn.close()
#     return {"message": "User created successfully"}

# @app.post("/token", response_model=Token)
# async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
#     # Use email instead of username
#     user = authenticate_user(form_data.username, form_data.password)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect email or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = create_access_token(
#         data={"sub": user['email']}, expires_delta=access_token_expires
#     )
#     return {"access_token": access_token, "token_type": "bearer"}

# @app.get("/users/me", response_model=dict)
# async def read_users_me(current_user: dict = Depends(get_current_active_user)):
#     return current_user

# @app.get("/users/me/items/")
# async def read_own_items(current_user: dict = Depends(get_current_active_user)):
#     return [{"item_id": 1, "owner": current_user['email']}]


from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import timedelta
from passlib.context import CryptContext
from typing import Optional
import os
from dotenv import load_dotenv
import mysql.connector
from fastapi.middleware.cors import CORSMiddleware
from chat.websocket import router as chat_ws_router
from db import get_db_connection, init_db_schema
from auth import get_current_active_user, create_access_token, get_user_by_email

# Load environment variables
load_dotenv()
init_db_schema()

# Validate required environment variables
# required_env_vars = [
#     "SECRET_KEY", "ALGORITHM", "ACCESS_TOKEN_EXPIRE_MINUTES",
#     "MYSQLHOST", "MYSQLUSER", "MYSQLPASSWORD", "MYSQLDATABASE"
# ]
required_env_vars = [
    "SECRET_KEY", "ALGORITHM", "ACCESS_TOKEN_EXPIRE_MINUTES",
    "DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"
]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Configuration
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

# FastAPI app and security
app = FastAPI()
app.include_router(chat_ws_router)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

origins = [
    "http://localhost:3000",  # local
    "https://coinconnect.vercel.app",  # production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class User(BaseModel):
    username: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user or not verify_password(password, user['hashed_password']):
        return False
    return user

# Routes
@app.get("/")
def home():
    return "WELCOME HERE!"

@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: User):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = get_password_hash(user.password)
    try:
        cursor.execute(
            "INSERT INTO users (username, email, hashed_password) VALUES (%s, %s, %s)",
            (user.username, user.email, hashed_password)
        )
        conn.commit()
    except mysql.connector.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )
    finally:
        cursor.close()
        conn.close()
    return {"message": "User created successfully"}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Use email instead of username
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['email']}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=dict)
async def read_users_me(current_user: dict = Depends(get_current_active_user)):
    return current_user

@app.get("/users/me/items/")
async def read_own_items(current_user: dict = Depends(get_current_active_user)):
    return [{"item_id": 1, "owner": current_user['email']}]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=int(os.getenv("PORT", 8001)))