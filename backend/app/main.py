from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app import models, schemas, security
from app.database import engine, get_db

# Inicialización de base de datos
models.Base.metadata.create_all(bind=engine)

# CONFIGURACIÓN DEL RATE LIMITER (Usa la IP del usuario)
limiter = Limiter(key_func=get_remote_address)

# Inicialización de la aplicación
app = FastAPI(
    title="API Principal",
    description="Backend operativo con Base de Datos Real",
    version="1.0.0"
)

# REGISTRO DEL LIMITADOR EN LA APP
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de seguridad para lectura de tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Endpoints públicos
@app.get("/")
def health_check():
    return {"status": "ok", "message": "Backend operativo al 100%"}

@app.post("/usuarios", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    hashed_password = security.get_password_hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_password)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# Autenticación y login (Protegido por Rate Limit: 10 peticiones por minuto)
@app.post("/login", response_model=schemas.Token)
@limiter.limit("10/minute") # <-- EL ESCUDO DE RED
@app.post("/login", response_model=schemas.Token)
@limiter.limit("10/minute")
def login(request: Request, user_credentials: schemas.LoginRequest, db: Session = Depends(get_db)):
    # Capturamos la IP del usuario de forma silenciosa
    client_ip = request.client.host
    print(f"Intento de login desde la IP: {client_ip}")

    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )

    if user.locked_until and user.locked_until > datetime.utcnow():
        tiempo_restante = (user.locked_until - datetime.utcnow()).seconds // 60
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cuenta bloqueada. Intenta en {tiempo_restante + 1} minutos."
        )

    if not security.verify_password(user_credentials.password, user.hashed_password):
        user.failed_attempts += 1
        
        if user.failed_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cuenta bloqueada por 15 minutos debido a múltiples intentos fallidos."
            )
            
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Credenciales incorrectas. Intentos restantes: {5 - user.failed_attempts}"
        )

    user.failed_attempts = 0
    user.locked_until = None
    db.commit()

    # Generación de ambos tokens (Acceso y Renovación)
    access_token = security.create_access_token(
        data={"sub": user.email}, 
        remember_me=user_credentials.rememberMe
    )
    refresh_token = security.create_refresh_token(
        data={"sub": user.email}
    )
    
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

# Dependencia de validación de token JWT
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
        
    return user

# Rutas protegidas
@app.get("/api/dashboard/stats")
def get_dashboard_stats(current_user: models.User = Depends(get_current_user)):
    return {
        "mensaje": f"¡Acceso concedido! Bienvenido, {current_user.email}",
        "data": {
            "ventas_hoy": 150,
            "stock_critico": 3
        }
    }

# RENOVACIÓN DE SESIÓN (Refresh Token)
from pydantic import BaseModel

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@app.post("/refresh", response_model=schemas.Token)
def refresh_session(request_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Desencriptamos el refresh token
        payload = jwt.decode(request_data.refresh_token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        # Validamos que sí sea un refresh token y no uno de acceso
        if email is None or token_type != "refresh":
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
        
    # Verificamos que el usuario aún exista
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception
        
    # Si todo es correcto, generamos un nuevo par de tokens
    new_access_token = security.create_access_token(data={"sub": user.email})
    new_refresh_token = security.create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }