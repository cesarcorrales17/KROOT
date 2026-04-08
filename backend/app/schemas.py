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

# MODELOS PARA RECUPERACIÓN DE CONTRASEÑA
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

    # Reutilizamos tu validador estricto para la nueva contraseña
    @field_validator('new_password')
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
        

# WIZARD DE CONFIGURACIÓN DE LA EMPRESA
# Esquema para el "Guardado Automático" (Todos los campos son opcionales)
class BusinessSetupPartial(BaseModel):
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    industry: Optional[str] = None
    estimated_income: Optional[int] = None
    estimated_expenses: Optional[int] = None
    tracking_frequency: Optional[str] = None
    onboarding_completed: Optional[bool] = False

# Esquema de respuesta para enviarle a Angular cuando vuelva a entrar
class BusinessResponse(BaseModel):
    id: int
    user_id: int
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    industry: Optional[str] = None
    estimated_income: Optional[int] = None
    estimated_expenses: Optional[int] = None
    tracking_frequency: Optional[str] = None
    onboarding_completed: bool

    class Config:
        from_attributes = True