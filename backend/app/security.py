from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt

# CONFIGURACIÓN DE SEGURIDAD (JWT y Hashing)
SECRET_KEY = "tu_clave_secreta_super_segura_aqui" # Idealmente esto irá luego en un archivo .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15 # Tiempo base de sesión (para luego pedir relogin)
REMEMBER_ME_EXPIRE_DAYS = 7      # Sesión extendida ("Mantenerme conectado")

# Inicialización de bcrypt para encriptar/verificar contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# FUNCIONES DE CONTRASEÑA
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# GENERACIÓN DE TOKEN JWT
def create_access_token(data: dict, remember_me: bool = False) -> str:
    to_encode = data.copy()
    
    # Evalúa si el usuario seleccionó "Mantenerme conectado"
    if remember_me:
        expire = datetime.utcnow() + timedelta(days=REMEMBER_ME_EXPIRE_DAYS)
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    
    # Genera y firma el token con la clave secreta
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# CREACIÓN DE REFRESH TOKEN (Duración larga)
def create_refresh_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7) # Por defecto dura 7 días
        
    to_encode.update({"exp": expire, "type": "refresh"}) # Etiqueta interna para diferenciarlo
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt