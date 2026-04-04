from pydantic import BaseModel, EmailStr, Field
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

# MODELOS PARA CREACIÓN Y LECTURA DE USUARIOS
class UserCreate(BaseModel):
    email: EmailStr
    # NUEVO: Validación estricta de 8 caracteres
    password: str = Field(..., min_length=8, description="La contraseña debe tener al menos 8 caracteres")

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_verified: bool 
    created_at: datetime  

    class Config:
        from_attributes = True