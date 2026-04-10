from pydantic import BaseModel, EmailStr, Field, field_validator
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from datetime import date

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

# Esquema para actualizar el perfil del negocio
class BusinessProfileUpdate(BaseModel):
    business_name: str
    industry: str
    business_size: str
    currency: str
    
# Esquema de respuesta para enviarle a Angular cuando vuelva a entrar
class BusinessResponse(BaseModel):
    id: int
    user_id: int
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    industry: Optional[str] = None
    business_size: Optional[str] = None 
    currency: Optional[str] = None      
    estimated_income: Optional[int] = None
    estimated_expenses: Optional[int] = None
    tracking_frequency: Optional[str] = None
    onboarding_completed: bool

    class Config:
        from_attributes = True
        
        
# ESQUEMAS PARA EL DASHBOARD
class KPIStats(BaseModel):
    total_income: float
    total_expenses: float
    cash_flow: float

class ChartData(BaseModel):
    labels: List[str]
    income_data: List[float]
    expense_data: List[float]

class DashboardSummary(BaseModel):
    has_data: bool
    currency: str
    kpis: KPIStats
    charts: ChartData
    
    
# ESQUEMAS PARA VENTAS
class SaleCreate(BaseModel):
    amount: float
    period_type: str
    period_date: date
    category: Optional[str] = None
    payment_method: Optional[str] = None
    description: Optional[str] = None

class SaleResponse(BaseModel):
    id: int
    business_id: int
    amount: float
    period_type: str
    period_date: date
    
    class Config:
        from_attributes = True

class SalesSummary(BaseModel):
    current_period_amount: float
    previous_period_amount: float
    difference_amount: float
    difference_percentage: float
    trend: str # 'up', 'down', 'neutral'