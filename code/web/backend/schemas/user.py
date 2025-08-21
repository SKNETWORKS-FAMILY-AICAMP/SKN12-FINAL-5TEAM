# backend/schemas/user.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    pw: str

class UserLogin(BaseModel):
    email: EmailStr
    pw: str

class UserResponse(BaseModel):
    user_id: int
    name: str
    email: EmailStr

class UserNameUpdate(BaseModel):
    name: str

class UserEmailUpdate(BaseModel):
    email: EmailStr

class UserProfileUpdate(BaseModel):
    name: str
    email: EmailStr

class UserPasswordUpdate(BaseModel):
    pw: str

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: UserResponse
