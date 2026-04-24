from pydantic import BaseModel, EmailStr, Field, field_validator
import re
from typing import Optional, List
from datetime import datetime, date

# ==========================================
# MODELOS DE PETICIÓN (Entrada desde Angular)
# ==========================================
class LoginRequest(BaseModel):
    email: EmailStr          
    password: str            
    rememberMe: bool = False 

# ==========================================
# MODELOS DE RESPUESTA (Salida hacia Angular)
# ==========================================
class Token(BaseModel):
    access_token: str        
    refresh_token: str       
    token_type: str          

class TokenData(BaseModel):
    email: Optional[str] = None

# ==========================================
# MODELOS DE USUARIO
# ==========================================
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

# ==========================================
# MODELOS PARA RECUPERACIÓN DE CONTRASEÑA
# ==========================================
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

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

# ==========================================
# MODELO DE RESPUESTA DE USUARIO
# ==========================================
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_verified: bool 
    created_at: datetime  

    class Config:
        from_attributes = True
        

# ==========================================
# WIZARD DE CONFIGURACIÓN DE LA EMPRESA
# ==========================================
class BusinessSetupPartial(BaseModel):
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    industry: Optional[str] = None
    estimated_income: Optional[int] = None
    estimated_expenses: Optional[int] = None
    tracking_frequency: Optional[str] = None
    onboarding_completed: Optional[bool] = False

class BusinessProfileUpdate(BaseModel):
    business_name: str
    industry: str
    business_size: str
    currency: str
    
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
        
        
# ==========================================
# ESQUEMAS PARA EL DASHBOARD
# ==========================================
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
    
    
# ==========================================
# ESQUEMAS PARA REGISTRO FINANCIERO / VENTAS
# ==========================================
class SaleCreate(BaseModel):
    # Campos obligatorios core
    amount: float
    period_type: str
    period_date: date
    
    # Origen del dato (Vital para tu HU Dual)
    source: Optional[str] = "manual" 

    # Campos opcionales de clasificación
    category: Optional[str] = None
    payment_method: Optional[str] = None
    description: Optional[str] = None
    
    # Datos del cliente
    client_name: Optional[str] = None
    client_type: Optional[str] = None
    client_contact: Optional[str] = None
    client_document: Optional[str] = None
    
    # Detalle del producto
    product_name: Optional[str] = None
    quantity: Optional[float] = 1.0
    unit_price: Optional[float] = None
    
    # Información financiera
    payment_status: Optional[str] = None
    invoice_ref: Optional[str] = None


class SaleResponse(BaseModel):
    id: int
    business_id: int
    source: str
    amount: float
    period_type: str
    period_date: date
    
    # Opcionalmente podemos devolver más campos si el frontend los necesita luego, 
    # pero estos son los básicos para confirmar la transacción.
    
    class Config:
        from_attributes = True

class SalesSummary(BaseModel):
    current_period_amount: float
    previous_period_amount: float
    difference_amount: float
    difference_percentage: float
    trend: str # 'up', 'down', 'neutral'
    

# ==========================================
# ESQUEMAS PARA GASTOS OPERATIVOS
# ==========================================

class ExpenseCategoryBase(BaseModel):
    name: str
    is_default: bool = False

class ExpenseCategoryResponse(ExpenseCategoryBase):
    id: int
    business_id: Optional[int] = None

    class Config:
        from_attributes = True

class ExpenseCreate(BaseModel):
    amount: float
    category_id: int
    period_type: str
    period_date: date
    
    source: Optional[str] = "manual"
    supplier_name: Optional[str] = None
    description: Optional[str] = None
    receipt_ref: Optional[str] = None

class ExpenseResponse(BaseModel):
    id: int
    business_id: int
    category_id: int
    source: str
    amount: float
    period_type: str
    period_date: date
    
    class Config:
        from_attributes = True
        
class ExpenseSummaryCategory(BaseModel):
    category_name: str
    total_amount: float
    percentage: float

class ExpenseSummary(BaseModel):
    total_period_amount: float
    categories_breakdown: List[ExpenseSummaryCategory]
    

# ==========================================
# ESQUEMAS PARA CATÁLOGO DE PRODUCTOS
# ==========================================

class ProductCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_default: bool = False

class ProductCategoryResponse(ProductCategoryBase):
    id: int
    business_id: Optional[int] = None

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    sku: str
    barcode: Optional[str] = None
    description: Optional[str] = None 
    category_id: Optional[int] = None
    sale_price: float
    cost_price: float
    unit: str = "unidad"
    image_url: Optional[str] = None
    is_active: bool = True
    min_stock: float = 5.0
    stock: float = 0.0

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    sale_price: Optional[float] = None
    cost_price: Optional[float] = None
    unit: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    min_stock: Optional[float] = None
    stock: Optional[float] = None
class ProductResponse(ProductBase):
    id: int
    business_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
    
        
# ==========================================
# ESQUEMAS PARA VENTAS (POS)
# ==========================================

class SaleDetailCreate(BaseModel):
    product_id: int
    quantity: float
    unit_price: float

class SaleCreate(BaseModel):
    client_name: Optional[str] = None
    client_document: Optional[str] = None
    payment_method: str = "Efectivo"
    details: List[SaleDetailCreate]