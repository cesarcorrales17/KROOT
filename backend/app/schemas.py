from pydantic import BaseModel, EmailStr
from typing import Optional

# MODELOS DE PETICIÓN (Entrada desde Angular)
class LoginRequest(BaseModel):
    email: EmailStr          # Valida formato de correo automáticamente
    password: str            # Contraseña del formulario
    rememberMe: bool = False # Casilla de mantener sesión

# MODELOS DE RESPUESTA (Salida hacia Angular)
class Token(BaseModel):
    access_token: str        # Token JWT para autenticación
    refresh_token: str       # Llave maestra para renovar sesión
    token_type: str          # Tipo de token (ej. "bearer")

class TokenData(BaseModel):
    email: Optional[str] = None

# MODELOS PARA CREACIÓN Y LECTURA DE USUARIOS
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool

    class Config:
        from_attributes = True # Permite a Pydantic leer modelos de SQLAlchemy