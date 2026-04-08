from pydantic import BaseModel, EmailStr, Field, field_validator
import re
from typing import Optional
from datetime import datetime

# MODELOS DE PETICIÓN (Entrada desde Angular)
class LoginRequest(BaseModel):
    email: EmailStr          
    password: str            
    rememberMe: bool = False 

# MODELOS DE RESPUESTA (Salida hacia Angular)
class Token(BaseModel):
    access_token: str        
    refresh_token: str       
    token_type: str          

class TokenData(BaseModel):
    email: Optional[str] = None

# MODELOS DE USUARIO
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not re.search(r'[0-9]', v):
            raise ValueError('La contraseña debe contener al menos un número')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('La contraseña debe contener al menos un carácter especial')
        return v

# MODELO DE RESPUESTA DE USUARIO
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_verified: bool 
    created_at: datetime  

    class Config:
        from_attributes = True