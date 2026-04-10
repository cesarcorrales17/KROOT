from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import JWTError, jwt
from datetime import datetime, timedelta
import uuid

# Librerías para Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Importaciones internas
from app import models, schemas, security, email_service
from app.database import engine, get_db
from app.business_rules import SECTOR_CONFIGS, BUSINESS_TYPES

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


# ==========================================
# NUEVO ENDPOINT DE REGISTRO ACTUALIZADO CON ENVÍO DE CORREO
# ==========================================

# Endpoint de registro de usuario con envío de correo de verificación
@app.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute") # Protegemos también la creación de cuentas
def register_user(request: Request, user: schemas.UserCreate, db: Session = Depends(get_db)):
    
    # 1. Verificar si el correo ya existe
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    # 2. Encriptar contraseña
    hashed_password = security.get_password_hash(user.password)
    
    # 3. Crear usuario (is_verified se pone en False por defecto gracias al modelo)
    new_user = models.User(email=user.email, hashed_password=hashed_password)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # --- 4. NUEVA LÓGICA DE CORREO ---
    # Generamos el token de verificación
    verification_token = security.create_email_verification_token(email=new_user.email)
    
    # Enviamos el correo simulado (Se imprimirá en la consola)
    email_service.send_verification_email(email=new_user.email, token=verification_token)
    # ---------------------------------
    
    return new_user

# NUEVO ENDPOINT PARA VERIFICAR EL CORREO TRAS EL CLIC
@app.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    try:
        # Desencriptamos el token usando tu configuración de seguridad
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        # Validamos que sea específicamente un token de verificación de correo
        if email is None or token_type != "email_verification":
            raise HTTPException(status_code=400, detail="Token inválido")
            
    except JWTError:
        raise HTTPException(status_code=400, detail="El enlace de verificación es inválido o ha expirado")
        
    # Buscamos al usuario
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    # Verificamos si ya había activado la cuenta
    if user.is_verified:
        return {"message": "La cuenta ya había sido verificada anteriormente."}
        
    # Activamos la cuenta
    user.is_verified = True
    db.commit()
    
    return {"message": "¡Tu cuenta ha sido verificada con éxito! Ya puedes iniciar sesión."}

# Autenticación y login (Protegido por Rate Limit: 10 peticiones por minuto)
@app.post("/login", response_model=schemas.Token)
@limiter.limit("10/minute") # <-- EL ESCUDO DE RED
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
        "token_type": "bearer",
        "is_setup_completed": user.is_setup_completed
    }


# ==========================================
# ENDPOINTS DE RECUPERACIÓN DE CONTRASEÑA
# ==========================================

@app.post("/forgot-password")
@limiter.limit("3/minute") # Rate limit estricto para evitar spam masivo de correos
def forgot_password(request: Request, body: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    # 1. Buscamos al usuario de forma silenciosa
    user = db.query(models.User).filter(models.User.email == body.email).first()
    
    if user:
        # 2. Generamos un UUID seguro y único
        reset_token = uuid.uuid4().hex
        # 3. Expiración estricta de 30 minutos
        expiration = datetime.utcnow() + timedelta(minutes=30)
        
        # 4. Guardamos el token en la base de datos
        db_token = models.PasswordResetToken(
            user_id=user.id,
            token=reset_token,
            expires_at=expiration
        )
        db.add(db_token)
        db.commit()
        
        # 5. Enviamos el correo
        email_service.send_password_reset_email(email=user.email, token=reset_token)
    
    # 6. SEGURIDAD: Respondemos siempre lo mismo, exista o no el correo (Anti-enumeración)
    return {"message": "Si el correo está registrado en Kroot, recibirás un enlace de recuperación en los próximos minutos."}

# Endpoint para resetear la contraseña usando el token enviado por correo
@app.post("/reset-password")
@limiter.limit("5/minute")
def reset_password(request: Request, body: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    # 1. Buscar el token en la base de datos verificando 3 condiciones críticas:
    db_token = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == body.token,
        models.PasswordResetToken.used == False, # Que no haya sido usado
        models.PasswordResetToken.expires_at > datetime.utcnow() # Que no esté vencido
    ).first()
    
    if not db_token:
        raise HTTPException(status_code=400, detail="El enlace de recuperación es inválido, ya fue usado o ha expirado.")
        
    # 2. Obtener el usuario dueño del token
    user = db.query(models.User).filter(models.User.id == db_token.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        
    # 3. VALIDACIÓN DE NEGOCIO: La contraseña nueva no puede ser la misma que la anterior
    if security.verify_password(body.new_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="La nueva contraseña no puede ser igual a la anterior por motivos de seguridad.")
        
    # 4. Encriptar y actualizar contraseña
    user.hashed_password = security.get_password_hash(body.new_password)
    
    # 5. QUEMAR EL TOKEN: Marcarlo como usado para evitar ataques de repetición
    db_token.used = True
    
    # Opcional (Extra): Resetear bloqueos por si la cuenta estaba bloqueada por intentos fallidos
    user.failed_attempts = 0
    user.locked_until = None
    
    db.commit()
    
    # 6. NOTIFICACIÓN DE SEGURIDAD: Enviar correo avisando el cambio
    email_service.send_password_changed_notification(email=user.email)
    
    return {"message": "Tu contraseña ha sido actualizada exitosamente. Ya puedes iniciar sesión."}
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

# Endpoint para renovar tokens usando el refresh token
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
    
# ENDPOINTS PARA EL WIZARD DE CONFIGURACIÓN DE EMPRESA
@app.get("/business/sectors")
def get_business_sectors():
    """
    Devuelve la lista de sectores disponibles con sus descripciones 
    para armar la UI en Angular (Dropdowns o Tarjetas).
    """
    # Formateamos el diccionario para que sea fácil de iterar en Angular
    sectors_list = [
        {"id": key, "name": key.replace("_", " ").title(), "description": value["description"]}
        for key, value in SECTOR_CONFIGS.items()
    ]
    
    types_list = [
        {"id": key, "name": value}
        for key, value in BUSINESS_TYPES.items()
    ]
    
    return {
        "sectors": sectors_list,
        "business_types": types_list
    }

# WIZARD DE CONFIGURACIÓN DE EMPRESA
@app.get("/business/setup", response_model=schemas.BusinessResponse)
def get_business_setup(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user) # Asegúrate de usar la dependencia que obtiene tu usuario actual
):
    """
    Devuelve la configuración actual de la empresa. 
    Ideal para recargar los datos si el usuario cerró la pestaña a la mitad del wizard.
    """
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Aún no hay configuración de empresa para este usuario")
        
    return business

# Endpoint de guardado automático (Upsert) para el wizard de configuración de la empresa
@app.patch("/business/setup", response_model=schemas.BusinessResponse)
def update_business_setup(
    setup_data: schemas.BusinessSetupPartial, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """
    Endpoint de guardado automático (Upsert). Crea el registro si no existe, 
    o actualiza solo los campos enviados si ya existe.
    """
    # 1. Buscamos si ya existe un registro para esta empresa
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    
    # 2. Si no existe, lo creamos vacío y lo asociamos al usuario
    if not business:
        business = models.Business(user_id=current_user.id)
        db.add(business)
        # No hacemos commit aún, primero le inyectamos los datos del Frontend
        
    # 3. Extraemos solo los datos que Angular nos envió en este paso específico (excluyendo nulos/vacíos)
    update_data = setup_data.model_dump(exclude_unset=True)
    
    # 4. Actualizamos el modelo dinámicamente
    for key, value in update_data.items():
        setattr(business, key, value)
        
    # 5. REGLA DE NEGOCIO CRÍTICA: Si el frontend avisa que el wizard terminó
    if setup_data.onboarding_completed:
        current_user.is_setup_completed = True
        
    db.commit()
    db.refresh(business)
    db.refresh(current_user) # Refrescamos el usuario por si cambió su estado
    
    return business


# ==========================================
# GESTIÓN DE PERFIL DEL NEGOCIO
# ==========================================

@app.get("/business/profile", response_model=schemas.BusinessResponse)
def get_business_profile(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Obtiene los datos actuales del negocio para precargarlos en el formulario."""
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    return business

@app.put("/business/profile", response_model=schemas.BusinessResponse)
def update_business_profile(
    profile_data: schemas.BusinessProfileUpdate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Actualiza la información principal del negocio y dispara el recálculo."""
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    # Regla de negocio: Si el sector cambió, necesitamos recalibrar las alertas (aunque esto lo haremos en la TAREA 4)
    sector_changed = business.industry != profile_data.industry
        
    # Actualiza solo los campos relevantes (podemos expandir esto según lo que Angular envíe)
    business.business_name = profile_data.business_name
    business.industry = profile_data.industry
    business.business_size = profile_data.business_size
    business.currency = profile_data.currency
    
    db.commit()
    db.refresh(business)
    
    # TODO: Lógica de negocio (Impacto en el sistema)
    if sector_changed:
        # Aquí más adelante llamaremos a la función que recalibra las alertas:
        # engine.recalculate_thresholds(business.id, profile_data.industry)
        pass
        
    return business


# ==========================================
# ENDPOINTS PARA EL DASHBOARD
# ==========================================

@app.get("/dashboard/summary", response_model=schemas.DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Calcula los KPIs y los datos para los gráficos del Dashboard."""
    
    # 1. Buscamos el negocio del usuario
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    # 2. Buscamos las transacciones
    # Por ahora traemos todo, en el futuro filtraremos por el mes actual
    transactions = db.query(models.Transaction).filter(models.Transaction.business_id == business.id).all()
    
    # Si no hay transacciones, devolvemos el estado vacío (Empty State)
    if not transactions:
        return {
            "has_data": False,
            "currency": business.currency or "COP",
            "kpis": {"total_income": 0.0, "total_expenses": 0.0, "cash_flow": 0.0},
            "charts": {
                "labels": ["Semana 1", "Semana 2", "Semana 3", "Semana 4"],
                "income_data": [0, 0, 0, 0],
                "expense_data": [0, 0, 0, 0]
            }
        }

    # 3. Calcular KPIs reales (Lógica de Negocio)
    total_inc = sum(t.amount for t in transactions if t.transaction_type == 'ingreso')
    total_exp = sum(t.amount for t in transactions if t.transaction_type == 'gasto')
    
    # 4. Agrupar para los Gráficos (Agrupación simple simulada por ahora)
    # Aquí iría la lógica compleja de agrupar por mes/día usando itertools o pandas
    # Para arrancar, enviaremos los totales para asegurar que la gráfica pinte algo.
    
    return {
        "has_data": True,
        "currency": business.currency or "COP",
        "kpis": {
            "total_income": total_inc,
            "total_expenses": total_exp,
            "cash_flow": total_inc - total_exp
        },
        "charts": {
            "labels": ["Actual"], # Etiquetas del eje X
            "income_data": [total_inc],
            "expense_data": [total_exp]
        }
    }
    
   
# ==========================================
# ENDPOINTS PARA GESTIÓN DE VENTAS
# ==========================================

# Endpoint para crear un registro de venta con validación de monto positivo 
@app.post("/sales", response_model=schemas.SaleResponse)
def create_sale(
    sale_data: schemas.SaleCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Guarda un registro de ventas validando que el monto sea positivo."""
    if sale_data.amount < 0:
        raise HTTPException(status_code=400, detail="El monto de venta no puede ser negativo.")

    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    new_sale = models.Sale(
        business_id=business.id,
        amount=sale_data.amount,
        period_type=sale_data.period_type,
        period_date=sale_data.period_date
    )
    
    db.add(new_sale)
    db.commit()
    db.refresh(new_sale)
    
    return new_sale

# Endpoint para obtener el resumen de ventas comparando el período actual con el anterior, mostrando la diferencia porcentual y la tendencia visual (sube, baja, neutral).
@app.get("/sales/summary", response_model=schemas.SalesSummary)
def get_sales_summary(
    period_type: str = "monthly", 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """
    Obtiene las ventas del período actual y el anterior para calcular 
    la diferencia porcentual y la tendencia.
    """
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    
    # Traemos las ventas ordenadas de la más reciente a la más antigua
    sales = db.query(models.Sale)\
        .filter(models.Sale.business_id == business.id, models.Sale.period_type == period_type)\
        .order_by(models.Sale.period_date.desc())\
        .all()

    # Si no hay ventas, devolvemos todo en cero
    if not sales:
        return {
            "current_period_amount": 0.0,
            "previous_period_amount": 0.0,
            "difference_amount": 0.0,
            "difference_percentage": 0.0,
            "trend": "neutral"
        }

    # Asumimos que el primer registro es el actual y el segundo el anterior
    # (En una versión avanzada usaríamos lógica de fechas exacta con librerías como relativedelta)
    current_sale = sales[0].amount
    previous_sale = sales[1].amount if len(sales) > 1 else 0.0

    diff_amount = current_sale - previous_sale
    
    # Prevenir división por cero
    if previous_sale > 0:
        diff_percentage = (diff_amount / previous_sale) * 100
    else:
        diff_percentage = 100.0 if current_sale > 0 else 0.0

    # Definir tendencia visual
    if diff_amount > 0:
        trend = "up"
    elif diff_amount < 0:
        trend = "down"
    else:
        trend = "neutral"

    return {
        "current_period_amount": current_sale,
        "previous_period_amount": previous_sale,
        "difference_amount": diff_amount,
        "difference_percentage": round(diff_percentage, 2),
        "trend": trend
    }