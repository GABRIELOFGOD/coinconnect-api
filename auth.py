# auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
import os
from db import get_db_connection

# JWT configuration from environment
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class TokenData(BaseModel):
    email: Optional[str] = None

def get_user_by_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        return user
    finally:
        cursor.close()
        conn.close()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    """Verify JWT token - used for WebSocket authentication"""
    try:
        if not token:
            return None
            
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            return None
        
        user = get_user_by_email(email)
        return user
    except JWTError:
        return None

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # print(f"get_current_user called with token: {token[:20] + '...' if token else 'None'}")
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        # print("No token provided to get_current_user")
        raise credentials_exception
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        # print(f"Token decoded successfully for email: {email}")
        
        if not email:
            # print("No email found in token payload")
            raise credentials_exception
            
        token_data = TokenData(email=email)
    except JWTError as e:
        # print(f"JWT Error: {e}")
        raise credentials_exception

    user = get_user_by_email(email=token_data.email)
    if not user:
        # print(f"No user found for email: {token_data.email}")
        raise credentials_exception
        
    # print(f"User authenticated successfully: {user['email']}")
    return user

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    if current_user.get('disabled'):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user