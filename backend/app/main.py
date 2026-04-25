from fastapi.responses import RedirectResponse
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import JWTError, jwt
from datetime import datetime, timedelta, date
import uuid
from typing import List
import logging
import os

# Librerías para Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Librerías para Google OAuth
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Importaciones internas
from app import models, schemas, security, email_service
from app.database import engine, get_db, SessionLocal
from app.business_rules import SECTOR_CONFIGS, BUSINESS_TYPES

# Inicialización de base de datos
models.Base.metadata.create_all(bind=engine)

# CONFIGURACIÓN DEL RATE LIMITER (Usa la IP del usuario)
limiter = Limiter(key_func=get_remote_address)

# CONSTANTES GLOBALES
GOOGLE_CLIENT_ID = "TU_CLIENT_ID_DE_GOOGLE.apps.googleusercontent.com" # Recuerda cambiar esto luego por tu ID real

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

# Configuración de logging para la inicialización
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kroot.startup")

def init_default_expense_categories(db: Session):
    try:
        default_names = [
            'Arriendo', 'Nómina', 'Servicios Públicos', 'Marketing / Publicidad', 
            'Insumos / Materia Prima', 'Mantenimiento', 'Logística y Envíos', 'Otros'
        ]
        existing_categories = db.query(models.ExpenseCategory.name).filter(
            models.ExpenseCategory.name.in_(default_names),
            models.ExpenseCategory.is_default == True
        ).all()
        existing_names = {cat[0] for cat in existing_categories}
        missing_categories = [
            models.ExpenseCategory(name=name, is_default=True)
            for name in default_names if name not in existing_names
        ]
        if missing_categories:
            db.add_all(missing_categories)
            db.commit()
            logger.info(f"Se agregaron {len(missing_categories)} categorias base al sistema.")
        else:
            logger.info("Las categorias base ya se encuentran sincronizadas.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error critico al inicializar categorias de gastos: {str(e)}")

def init_default_product_categories(db: Session):
    try:
        default_names = ['General', 'Servicios', 'Productos Fisicos', 'Insumos']
        existing_categories = db.query(models.ProductCategory.name).filter(
            models.ProductCategory.name.in_(default_names),
            models.ProductCategory.is_default == True
        ).all()
        existing_names = {cat[0] for cat in existing_categories}
        missing_categories = [
            models.ProductCategory(name=name, is_default=True)
            for name in default_names if name not in existing_names
        ]
        if missing_categories:
            db.add_all(missing_categories)
            db.commit()
            logger.info(f"Se agregaron {len(missing_categories)} categorias de productos base al sistema.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error critico al inicializar categorias de productos: {str(e)}")
        
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        init_default_expense_categories(db)
        init_default_product_categories(db) 
    finally:
        db.close()

# ==========================================
# SEGURIDAD Y AUTENTICACIÓN
# ==========================================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Backend operativo al 100%"}

# ==========================================
# REGISTRO CON AUTOLOGIN Y CORREO
# ==========================================
@app.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register_user(request: Request, user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    hashed_password = security.get_password_hash(user.password)
    client_ip = request.client.host # TAREA: Guardar IP inicial
    
    new_user = models.User(
        email=user.email, 
        hashed_password=hashed_password,
        last_login_ip=client_ip
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    verification_token = security.create_email_verification_token(email=new_user.email)
    email_service.send_verification_email(email=new_user.email, token=verification_token)
    
    # TAREA: Autologin después de registro
    access_token = security.create_access_token(data={"sub": new_user.email})
    refresh_token = security.create_refresh_token(data={"sub": new_user.email})
    
    return {
        "message": "Usuario registrado exitosamente. Verifica tu correo.",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {"id": new_user.id, "email": new_user.email}
    }

@app.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    FRONTEND_LOGIN_URL = "http://localhost:4200/login"
    
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None or token_type != "email_verification":
            # Si el token es falso, lo mandamos al login con un parámetro de error
            return RedirectResponse(url=f"{FRONTEND_LOGIN_URL}?error=invalid_token")
            
    except JWTError:
        return RedirectResponse(url=f"{FRONTEND_LOGIN_URL}?error=expired_token")
        
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return RedirectResponse(url=f"{FRONTEND_LOGIN_URL}?error=user_not_found")
        
    if user.is_verified:
        # Si ya estaba verificado, lo mandamos al login normalmente
        return RedirectResponse(url=f"{FRONTEND_LOGIN_URL}?verified=already")
        
    # Activamos la cuenta
    user.is_verified = True
    db.commit()
    
    # ÉXITO: Redirigimos mágicamente al Login de Angular indicando que fue exitoso
    return RedirectResponse(url=f"{FRONTEND_LOGIN_URL}?verified=true")

# TAREA: REENVIAR CORREO DE VERIFICACIÓN
@app.post("/resend-verification")
@limiter.limit("3/minute")
def resend_verification(request: Request, data: schemas.ResendVerificationRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user or user.is_verified:
        return {"message": "Si el correo está registrado y no verificado, se ha enviado un nuevo enlace."}
        
    verification_token = security.create_email_verification_token(email=user.email)
    email_service.send_verification_email(email=user.email, token=verification_token)
    return {"message": "Si el correo está registrado y no verificado, se ha enviado un nuevo enlace."}

# ==========================================
# LOGIN TRADICIONAL CON CONTROL DE IP
# ==========================================
@app.post("/login", response_model=schemas.Token)
@limiter.limit("10/minute")
def login(request: Request, user_credentials: schemas.LoginRequest, db: Session = Depends(get_db)):
    client_ip = request.client.host

    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    if user.locked_until and user.locked_until > datetime.utcnow():
        tiempo_restante = (user.locked_until - datetime.utcnow()).seconds // 60
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Cuenta bloqueada. Intenta en {tiempo_restante + 1} minutos.")

    if not security.verify_password(user_credentials.password, user.hashed_password):
        user.failed_attempts += 1
        if user.failed_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            db.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta bloqueada por 15 minutos debido a múltiples intentos fallidos.")
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Credenciales incorrectas. Intentos restantes: {5 - user.failed_attempts}")

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes verificar tu correo antes de iniciar sesión. Revisa tu bandeja de entrada."
        )
    
    user.failed_attempts = 0
    user.locked_until = None
    
    # TAREA: Registrar IP y notificar intento sospechoso
    if user.last_login_ip and user.last_login_ip != client_ip:
        logger.warning(f"ALERTA SEGURIDAD: Nuevo inicio de sesión desde IP diferente ({client_ip}) para {user.email}")
        # email_service.send_suspicious_login_email(user.email, client_ip)
    
    user.last_login_ip = client_ip
    db.commit()

    access_token = security.create_access_token(data={"sub": user.email}, remember_me=user_credentials.rememberMe)
    refresh_token = security.create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "is_setup_completed": user.is_setup_completed
    }

# ==========================================
# TAREA: REGISTRO Y LOGIN CON GOOGLE OAUTH
# ==========================================
@app.post("/auth/google")
def google_auth(request: Request, auth_data: schemas.GoogleAuthRequest, db: Session = Depends(get_db)):
    try:
        idinfo = id_token.verify_oauth2_token(auth_data.token, google_requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo['email']
        client_ip = request.client.host
        
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            # Registro nuevo con Google
            user = models.User(
                email=email,
                hashed_password="OAUTH_USER_NO_PASSWORD",
                is_verified=idinfo.get('email_verified', True),
                auth_provider="google",
                last_login_ip=client_ip
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Login existente con Google, validar IP
            if user.last_login_ip and user.last_login_ip != client_ip:
                logger.warning(f"ALERTA SEGURIDAD GOOGLE: Nuevo inicio de sesión ({client_ip}) para {user.email}")
            user.last_login_ip = client_ip
            db.commit()

        access_token = security.create_access_token(data={"sub": user.email})
        refresh_token = security.create_refresh_token(data={"sub": user.email})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {"email": user.email, "id": user.id},
            "is_setup_completed": user.is_setup_completed
        }
    except ValueError:
        raise HTTPException(status_code=401, detail="Token de Google inválido o expirado")


# ==========================================
# ENDPOINTS DE RECUPERACIÓN DE CONTRASEÑA
# ==========================================
@app.post("/forgot-password")
@limiter.limit("3/minute")
def forgot_password(request: Request, body: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    # 1. Búsqueda silenciosa de usuario
    user = db.query(models.User).filter(models.User.email == body.email).first()
    
    if user:
        # 2. Generación de token criptográficamente seguro
        reset_token = uuid.uuid4().hex
        
        # 3. Expiración estricta de 30 minutos
        expiration = datetime.utcnow() + timedelta(minutes=30)
        
        # 4. Almacenamiento y envío
        db_token = models.PasswordResetToken(user_id=user.id, token=reset_token, expires_at=expiration)
        db.add(db_token)
        db.commit()
        email_service.send_password_reset_email(email=user.email, token=reset_token)
        
    # 5. Seguridad: Respuesta genérica anti-enumeración
    return {"message": "Si el correo está registrado en Kroot, recibirás un enlace de recuperación en los próximos minutos."}

@app.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, body: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    # 1. Validación exhaustiva del token (Existencia, vigencia y que no esté usado)
    db_token = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == body.token,
        models.PasswordResetToken.used == False,
        models.PasswordResetToken.expires_at > datetime.utcnow()
    ).first()
    
    if not db_token:
        raise HTTPException(status_code=400, detail="El enlace de recuperación es inválido, ya fue usado o ha expirado.")
        
    user = db.query(models.User).filter(models.User.id == db_token.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        
    # 2. Validación de negocio: Evitar reutilizar la clave actual
    if security.verify_password(body.new_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="La nueva contraseña no puede ser igual a la anterior por motivos de seguridad.")
        
    # ----------------------------------------------------
    # EXTRAS DE SEGURIDAD: IP, Alertas y Sesiones
    # ----------------------------------------------------
    client_ip = request.client.host # Capturamos la IP de la solicitud de cambio
    
    # Notificar si la IP es inusual respecto al último login
    if user.last_login_ip and user.last_login_ip != client_ip:
        # Aquí podrías habilitar: email_service.send_suspicious_activity_email(user.email, client_ip)
        print(f"🚨 ALERTA CRÍTICA: Cambio de contraseña desde IP inusual ({client_ip}) para {user.email}")
        
    # Marcamos la fecha de cambio para invalidar automáticamente todos los tokens generados antes de este instante
    user.password_changed_at = datetime.utcnow()
    # ----------------------------------------------------

    # 3. Aplicar cambios y restaurar bloqueos
    user.hashed_password = security.get_password_hash(body.new_password)
    db_token.used = True
    user.failed_attempts = 0
    user.locked_until = None
    
    db.commit()
    email_service.send_password_changed_notification(email=user.email)
    
    return {"message": "Tu contraseña ha sido actualizada exitosamente. Ya puedes iniciar sesión."}

# ==========================================
# DEPENDENCIA DE SEGURIDAD (CANDADO PRINCIPAL)
# ==========================================
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales o tu sesión ha expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decodificación del token
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        token_issued_at = payload.get("iat") # Obtenemos la fecha de emisión del token (Issued At)
        
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
        
    # ----------------------------------------------------
    # EXTRA DE SEGURIDAD: Cerrar sesiones activas
    # ----------------------------------------------------
    # Si el usuario cambió su contraseña después de que este token fue emitido, lo rechazamos
    if token_issued_at and getattr(user, 'password_changed_at', None):
        issued_date = datetime.utcfromtimestamp(token_issued_at)
        # Margen de 1 segundo para evitar problemas de microsegundos
        if issued_date < (user.password_changed_at - timedelta(seconds=1)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tu sesión ha expirado debido a un cambio de contraseña reciente. Por favor, inicia sesión nuevamente."
            )
            
    return user

@app.get("/api/dashboard/stats")
def get_dashboard_stats(current_user: models.User = Depends(get_current_user)):
    return {
        "mensaje": f"¡Acceso concedido! Bienvenido, {current_user.email}",
        "data": {
            "ventas_hoy": 150,
            "stock_critico": 3
        }
    }

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
        payload = jwt.decode(request_data.refresh_token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        token_issued_at = payload.get("iat") # Fecha de emisión del refresh token
        
        if email is None or token_type != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception
        
    # ----------------------------------------------------
    # EXTRA DE SEGURIDAD: Evitar renovación si la clave cambió
    # ----------------------------------------------------
    if token_issued_at and getattr(user, 'password_changed_at', None):
        issued_date = datetime.utcfromtimestamp(token_issued_at)
        if issued_date < (user.password_changed_at - timedelta(seconds=1)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tu sesión ha expirado debido a un cambio de contraseña reciente. Por favor, inicia sesión nuevamente."
            )
            
    # Generar nuevos tokens
    new_access_token = security.create_access_token(data={"sub": user.email})
    new_refresh_token = security.create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }
# ==========================================
# WIZARD DE CONFIGURACIÓN DE EMPRESA
# ==========================================
@app.get("/business/sectors")
def get_business_sectors():
    sectors_list = [
        {"id": key, "name": key.replace("_", " ").title(), "description": value["description"]}
        for key, value in SECTOR_CONFIGS.items()
    ]
    types_list = [
        {"id": key, "name": value}
        for key, value in BUSINESS_TYPES.items()
    ]
    return {"sectors": sectors_list, "business_types": types_list}

@app.get("/business/setup", response_model=schemas.BusinessResponse)
def get_business_setup(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Aún no hay configuración de empresa para este usuario")
    return business

@app.patch("/business/setup", response_model=schemas.BusinessResponse)
def update_business_setup(setup_data: schemas.BusinessSetupPartial, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        business = models.Business(user_id=current_user.id)
        db.add(business)
        
    update_data = setup_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(business, key, value)
        
    if setup_data.onboarding_completed:
        current_user.is_setup_completed = True
        
    db.commit()
    db.refresh(business)
    db.refresh(current_user)
    return business

# ==========================================
# GESTIÓN DE PERFIL DEL NEGOCIO
# ==========================================
@app.get("/business/profile", response_model=schemas.BusinessResponse)
def get_business_profile(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    return business

@app.put("/business/profile", response_model=schemas.BusinessResponse)
def update_business_profile(profile_data: schemas.BusinessProfileUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    sector_changed = business.industry != profile_data.industry
    business.business_name = profile_data.business_name
    business.industry = profile_data.industry
    business.business_size = profile_data.business_size
    business.currency = profile_data.currency
    db.commit()
    db.refresh(business)
    return business

# ==========================================
# ENDPOINTS PARA EL DASHBOARD
# ==========================================
@app.get("/dashboard/summary", response_model=schemas.DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    sales = db.query(models.Sale).filter(models.Sale.business_id == business.id).all()
    dias_semana = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Hoy"]
    
    if not sales:
        return {
            "has_data": False,
            "currency": business.currency or "COP",
            "kpis": {"total_income": 0.0, "total_expenses": 0.0, "cash_flow": 0.0},
            "charts": {"labels": dias_semana, "income_data": [0,0,0,0,0,0,0], "expense_data": [0,0,0,0,0,0,0]}
        }

    total_inc = sum(s.amount for s in sales)
    total_exp = 0.0 
    
    return {
        "has_data": True,
        "currency": business.currency or "COP",
        "kpis": {"total_income": total_inc, "total_expenses": total_exp, "cash_flow": total_inc - total_exp},
        "charts": {"labels": dias_semana, "income_data": [0,0,0,0,0,0,total_inc], "expense_data": [0,0,0,0,0,0,total_exp]}
    }
   
# ==========================================
# ENDPOINTS PARA GESTIÓN DE VENTAS
# ==========================================
@app.post("/sales/manual", response_model=schemas.SaleResponse)
def create_manual_sale(sale_data: schemas.SaleCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if sale_data.amount < 0:
        raise HTTPException(status_code=400, detail="El monto de venta no puede ser negativo.")

    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    new_sale = models.Sale(
        business_id=business.id,
        source="manual",
        amount=sale_data.amount,
        period_type=sale_data.period_type,
        period_date=sale_data.period_date,
        category=sale_data.category,
        payment_method=sale_data.payment_method,
        description=sale_data.description,
        client_name=sale_data.client_name,
        client_type=sale_data.client_type,
        client_contact=sale_data.client_contact,
        client_document=sale_data.client_document,
        product_name=sale_data.product_name,
        quantity=sale_data.quantity,
        unit_price=sale_data.unit_price,
        payment_status=sale_data.payment_status,
        invoice_ref=sale_data.invoice_ref
    )
    db.add(new_sale)
    db.commit()
    db.refresh(new_sale)
    return new_sale

@app.get("/sales/summary", response_model=schemas.SalesSummary)
def get_sales_summary(period_type: str = "monthly", db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    
    sales = db.query(models.Sale).filter(models.Sale.business_id == business.id, models.Sale.period_type == period_type).order_by(models.Sale.period_date.desc()).all()
    if not sales:
        return {"current_period_amount": 0.0, "previous_period_amount": 0.0, "difference_amount": 0.0, "difference_percentage": 0.0, "trend": "neutral"}

    grouped_sales = {}
    for sale in sales:
        date_str = sale.period_date.strftime("%Y-%m-%d")
        if date_str not in grouped_sales:
            grouped_sales[date_str] = 0.0
        grouped_sales[date_str] += sale.amount

    unique_periods = sorted(grouped_sales.keys(), reverse=True)
    current_sale = grouped_sales[unique_periods[0]]
    previous_sale = grouped_sales[unique_periods[1]] if len(unique_periods) > 1 else 0.0

    diff_amount = current_sale - previous_sale
    diff_percentage = (diff_amount / previous_sale) * 100 if previous_sale > 0 else (100.0 if current_sale > 0 else 0.0)

    trend = "up" if diff_amount > 0 else "down" if diff_amount < 0 else "neutral"

    return {"current_period_amount": current_sale, "previous_period_amount": previous_sale, "difference_amount": diff_amount, "difference_percentage": round(diff_percentage, 2), "trend": trend}
    
# ==========================================
# ENDPOINTS PARA GESTIÓN DE GASTOS
# ==========================================
@app.get("/expenses/categories", response_model=List[schemas.ExpenseCategoryResponse])
def get_expense_categories(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    categories = db.query(models.ExpenseCategory).filter((models.ExpenseCategory.business_id == None) | (models.ExpenseCategory.business_id == business.id)).all()
    return categories

@app.post("/expenses/categories", response_model=schemas.ExpenseCategoryResponse)
def create_expense_category(category_data: schemas.ExpenseCategoryBase, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    new_category = models.ExpenseCategory(business_id=business.id, name=category_data.name, is_default=False)
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

@app.post("/expenses/manual", response_model=schemas.ExpenseResponse)
def create_manual_expense(expense_data: schemas.ExpenseCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if expense_data.amount <= 0:
        raise HTTPException(status_code=400, detail="El monto del gasto debe ser mayor a cero.")
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    new_expense = models.Expense(
        business_id=business.id,
        category_id=expense_data.category_id,
        source="manual",
        amount=expense_data.amount,
        period_type=expense_data.period_type,
        period_date=expense_data.period_date,
        supplier_name=expense_data.supplier_name,
        description=expense_data.description,
        receipt_ref=expense_data.receipt_ref
    )
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)
    return new_expense

@app.get("/expenses/summary", response_model=schemas.ExpenseSummary)
def get_expenses_summary(period_type: str = "monthly", db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    expenses = db.query(models.Expense).filter(models.Expense.business_id == business.id, models.Expense.period_type == period_type).all()
    total_amount = sum(e.amount for e in expenses)
    if total_amount == 0:
        return {"total_period_amount": 0.0, "categories_breakdown": []}

    category_totals = {}
    for expense in expenses:
        cat_name = expense.category.name if expense.category else "Sin Categoría"
        category_totals[cat_name] = category_totals.get(cat_name, 0.0) + expense.amount

    breakdown = [{"category_name": name, "total_amount": amount, "percentage": round((amount / total_amount) * 100, 2)} for name, amount in category_totals.items()]
    breakdown.sort(key=lambda x: x["total_amount"], reverse=True)

    return {"total_period_amount": total_amount, "categories_breakdown": breakdown}

# ==========================================
# ENDPOINTS PARA CATÁLOGO E INVENTARIO
# ==========================================
@app.post("/products", response_model=schemas.ProductResponse)
def create_product(product_data: schemas.ProductCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    existing_product = db.query(models.Product).filter(models.Product.business_id == business.id, models.Product.sku == product_data.sku).first()
    if existing_product:
        raise HTTPException(status_code=400, detail="Ya existe un producto registrado con este SKU.")

    new_product = models.Product(business_id=business.id, **product_data.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

@app.get("/products", response_model=List[schemas.ProductResponse])
def get_products(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    return db.query(models.Product).filter(models.Product.business_id == business.id).all()

@app.put("/products/{product_id}", response_model=schemas.ProductResponse)
def update_product(product_id: int, product_data: schemas.ProductUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    product = db.query(models.Product).filter(models.Product.id == product_id, models.Product.business_id == business.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if product_data.sku and product_data.sku != product.sku:
        existing_product = db.query(models.Product).filter(models.Product.business_id == business.id, models.Product.sku == product_data.sku).first()
        if existing_product:
            raise HTTPException(status_code=400, detail="El nuevo SKU ya está en uso por otro producto.")

    update_data = product_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product

@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    product = db.query(models.Product).filter(models.Product.id == product_id, models.Product.business_id == business.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    db.delete(product)
    db.commit()
    return {"message": "Producto eliminado exitosamente"}

@app.patch("/products/{product_id}/status", response_model=schemas.ProductResponse)
def toggle_product_status(product_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    product = db.query(models.Product).filter(models.Product.id == product_id, models.Product.business_id == business.id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    product.is_active = not product.is_active
    db.commit()
    db.refresh(product)
    return product

# ==========================================
# ENDPOINTS DE VENTAS (POS)
# ==========================================
@app.post("/sales/pos")
def create_pos_sale(sale_data: schemas.SalePosCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    if not sale_data.details:
        raise HTTPException(status_code=400, detail="El carrito de compras está vacío.")

    total_sale = 0.0
    new_sale = models.Sale(
        business_id=business.id,
        source="pos",
        amount=0.0,
        period_type="monthly", 
        period_date=date.today(),
        category="Venta de Inventario",
        client_name=sale_data.client_name or "Cliente General",
        client_document=sale_data.client_document,
        payment_method=sale_data.payment_method,
        payment_status="Pagado"
    )
    db.add(new_sale)
    db.flush()

    for item in sale_data.details:
        product = db.query(models.Product).filter(models.Product.id == item.product_id, models.Product.business_id == business.id).with_for_update().first() 
        if not product:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Producto no encontrado.")
        if product.stock < item.quantity:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para: {product.name}. Disponible: {product.stock}")

        product.stock -= item.quantity
        subtotal = item.quantity * item.unit_price
        total_sale += subtotal

        new_detail = models.SaleDetail(
            sale_id=new_sale.id,
            product_id=product.id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=subtotal
        )
        db.add(new_detail)

    new_sale.amount = total_sale
    db.commit()
    return {"message": "Venta procesada con éxito", "sale_id": new_sale.id, "total": total_sale}
    
# ==========================================
# TAREA: MOVIMIENTOS DE INVENTARIO (AJUSTES)
# ==========================================
@app.post("/api/inventory/movements", status_code=status.HTTP_201_CREATED)
def create_inventory_movement(movement_data: schemas.MovementCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    product = db.query(models.Product).filter(models.Product.id == movement_data.product_id, models.Product.business_id == business.id).with_for_update().first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if movement_data.quantity <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a cero")

    if movement_data.type == "OUT" and product.stock < movement_data.quantity:
        raise HTTPException(status_code=400, detail=f"Stock insuficiente. Disponible: {product.stock} {product.unit}")

    if movement_data.type == "IN":
        product.stock += movement_data.quantity
    else:
        product.stock -= movement_data.quantity

    new_movement = models.InventoryMovement(
        product_id=product.id,
        business_id=business.id,
        user_id=current_user.id,
        type=movement_data.type,
        quantity=movement_data.quantity,
        reason=movement_data.reason
    )

    db.add(new_movement)
    db.commit()
    db.refresh(product)

    return {"message": "Movimiento registrado correctamente", "new_stock": product.stock, "is_low_stock": product.stock <= product.min_stock}

@app.get("/api/inventory/movements/{product_id}", response_model=List[schemas.MovementResponse])
def get_inventory_history(product_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    return db.query(models.InventoryMovement).filter(models.InventoryMovement.product_id == product_id, models.InventoryMovement.business_id == business.id).order_by(models.InventoryMovement.created_at.desc()).all()


# ==========================================
# ENDPOINTS DEL DASHBOARD (ÉPICA 15)
# ==========================================
@app.get("/api/dashboard/financial")
def get_dashboard_financial(period: str = "this_month", db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    total_income = db.query(func.sum(models.SaleDetail.subtotal)).join(models.Sale, models.SaleDetail.sale_id == models.Sale.id).filter(models.Sale.business_id == business.id).scalar() or 0.0
    total_expenses = db.query(func.sum(models.Expense.amount)).filter(models.Expense.business_id == business.id).scalar() or 0.0
    cash_flow = total_income - total_expenses

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "cash_flow": cash_flow,
        "chart_labels": ["Semana 1", "Semana 2", "Semana 3", "Semana 4"],
        "chart_incomes": [total_income * 0.1, total_income * 0.2, total_income * 0.3, total_income * 0.4] if total_income > 0 else [0,0,0,0],
        "chart_expenses": [total_expenses * 0.1, total_expenses * 0.2, total_expenses * 0.3, total_expenses * 0.4] if total_expenses > 0 else [0,0,0,0]
    }

@app.get("/api/dashboard/operational")
def get_dashboard_operational(period: str = "this_month", db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    low_stock_alerts = db.query(models.Product).filter(models.Product.business_id == business.id, models.Product.stock <= models.Product.min_stock).count()
    today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
    units_sold_today = db.query(func.sum(models.SaleDetail.quantity)).join(models.Sale, models.SaleDetail.sale_id == models.Sale.id).filter(models.Sale.business_id == business.id, models.Sale.created_at >= today_start).scalar() or 0
    top_sales = db.query(
        models.Product.name, func.sum(models.SaleDetail.quantity).label('total_sold'), func.sum(models.SaleDetail.subtotal).label('total_revenue')
    ).join(models.SaleDetail, models.Product.id == models.SaleDetail.product_id).join(models.Sale, models.SaleDetail.sale_id == models.Sale.id).filter(models.Sale.business_id == business.id).group_by(models.Product.id, models.Product.name).order_by(func.sum(models.SaleDetail.quantity).desc()).limit(5).all()

    top_products = [{"name": item.name, "sold": int(item.total_sold), "revenue": float(item.total_revenue)} for item in top_sales]

    return {
        "units_sold_today": int(units_sold_today),
        "low_stock_alerts": low_stock_alerts,
        "active_branches": 1,
        "top_products": top_products
    }