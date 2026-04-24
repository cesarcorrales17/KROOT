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

# Librerías para Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Importaciones internas
from app import models, schemas, security, email_service
from app.database import engine, get_db, SessionLocal
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

# Configuración de logging para la inicialización
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kroot.startup")

def init_default_expense_categories(db: Session):
    """
    Verifica e inyecta las categorias de gastos por defecto para cualquier tipo de negocio.
    Usa inserciones en bloque para optimizar el rendimiento.
    """
    try:
        # Categorías estándar para cualquier modelo de negocio
        default_names = [
            'Arriendo', 
            'Nómina', 
            'Servicios Públicos', 
            'Marketing / Publicidad', 
            'Insumos / Materia Prima', 
            'Mantenimiento',
            'Logística y Envíos',
            'Otros'
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

# Inicializamos las categorías por defecto al arrancar la aplicación
def init_default_product_categories(db: Session):
    """
    Verifica e inyecta las categorias de productos por defecto.
    """
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
    """Calcula los KPIs y los datos para los gráficos del Dashboard leyendo la nueva tabla Sale."""
    
    # 1. Buscamos el negocio del usuario
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    # 2. Buscamos las ventas reales en la tabla correcta (Sale)
    sales = db.query(models.Sale).filter(models.Sale.business_id == business.id).all()
    
    # ARRAY BASE: Días de la semana para que la gráfica tenga un eje X
    dias_semana = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Hoy"]
    
    # Si no hay ventas, devolvemos el estado vacío
    if not sales:
        return {
            "has_data": False,
            "currency": business.currency or "COP",
            "kpis": {"total_income": 0.0, "total_expenses": 0.0, "cash_flow": 0.0},
            "charts": {
                "labels": dias_semana,
                "income_data": [0, 0, 0, 0, 0, 0, 0],
                "expense_data": [0, 0, 0, 0, 0, 0, 0]
            }
        }

    # 3. Calcular KPIs reales (Sumamos todos los montos de la tabla Sale)
    total_inc = sum(s.amount for s in sales)
    
    # Los gastos serán 0 hasta que hagamos la pantalla de "Registrar Gastos"
    total_exp = 0.0 
    
    # 4. Retornamos los datos armados para las gráficas
    return {
        "has_data": True,
        "currency": business.currency or "COP",
        "kpis": {
            "total_income": total_inc,
            "total_expenses": total_exp,
            "cash_flow": total_inc - total_exp
        },
        "charts": {
            "labels": dias_semana, 
            "income_data": [0, 0, 0, 0, 0, 0, total_inc],
            "expense_data": [0, 0, 0, 0, 0, 0, total_exp]
        }
    }
   
# ==========================================
# ENDPOINTS PARA GESTIÓN DE VENTAS
# ==========================================

@app.post("/sales/manual", response_model=schemas.SaleResponse)
def create_manual_sale(
    sale_data: schemas.SaleCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Guarda un registro de ventas ingresado manualmente (Fallback) con todos sus detalles."""
    
    if sale_data.amount < 0:
        raise HTTPException(status_code=400, detail="El monto de venta no puede ser negativo.")

    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    # Mapeamos TODOS los campos de la base de datos que limpiamos en el modelo
    new_sale = models.Sale(
        business_id=business.id,
        source="manual", # Forzamos que cumpla la HU indicando que es digitado a mano
        
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
def get_sales_summary(
    period_type: str = "monthly", 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """
    Obtiene TODAS las ventas (Manuales y POS) agrupadas por período actual vs anterior 
    para calcular la diferencia porcentual real del negocio.
    """
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")
    
    # Traemos las ventas ordenadas de la más reciente a la más antigua
    sales = db.query(models.Sale)\
        .filter(models.Sale.business_id == business.id, models.Sale.period_type == period_type)\
        .order_by(models.Sale.period_date.desc())\
        .all()

    # Si no hay ventas, devolvemos todo en cero para el estado vacío
    if not sales:
        return {
            "current_period_amount": 0.0,
            "previous_period_amount": 0.0,
            "difference_amount": 0.0,
            "difference_percentage": 0.0,
            "trend": "neutral"
        }

    # AGRUPACIÓN LÓGICA: Como ahora habrá múltiples ventas por día/mes, debemos sumarlas.
    grouped_sales = {}
    for sale in sales:
        # Usamos la fecha como llave agrupadora
        date_str = sale.period_date.strftime("%Y-%m-%d")
        if date_str not in grouped_sales:
            grouped_sales[date_str] = 0.0
        grouped_sales[date_str] += sale.amount

    # Obtenemos los períodos únicos, ordenados del más reciente al más antiguo
    unique_periods = sorted(grouped_sales.keys(), reverse=True)

    # El índice 0 es el período actual, el índice 1 es el período anterior
    current_sale = grouped_sales[unique_periods[0]]
    previous_sale = grouped_sales[unique_periods[1]] if len(unique_periods) > 1 else 0.0

    diff_amount = current_sale - previous_sale
    
    # Prevenir división por cero matemáticamente
    if previous_sale > 0:
        diff_percentage = (diff_amount / previous_sale) * 100
    else:
        diff_percentage = 100.0 if current_sale > 0 else 0.0

    # Definir tendencia visual para la UI
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
    
    
# ==========================================
# ENDPOINTS PARA GESTIÓN DE GASTOS
# ==========================================

@app.get("/expenses/categories", response_model=List[schemas.ExpenseCategoryResponse])
def get_expense_categories(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Obtiene las categorías de gastos predefinidas y las personalizadas de la empresa."""
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    # Trae categorías globales (business_id == None) y las creadas por este negocio
    categories = db.query(models.ExpenseCategory).filter(
        (models.ExpenseCategory.business_id == None) | 
        (models.ExpenseCategory.business_id == business.id)
    ).all()
    
    return categories

@app.post("/expenses/categories", response_model=schemas.ExpenseCategoryResponse)
def create_expense_category(
    category_data: schemas.ExpenseCategoryBase, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Crea una nueva categoría de gasto personalizada para la empresa."""
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    new_category = models.ExpenseCategory(
        business_id=business.id,
        name=category_data.name,
        is_default=False # Las creadas por el usuario no son globales
    )
    
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    return new_category

@app.post("/expenses/manual", response_model=schemas.ExpenseResponse)
def create_manual_expense(
    expense_data: schemas.ExpenseCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Guarda un registro de gasto operativo ingresado manualmente."""
    if expense_data.amount <= 0:
        raise HTTPException(status_code=400, detail="El monto del gasto debe ser mayor a cero.")

    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    new_expense = models.Expense(
        business_id=business.id,
        category_id=expense_data.category_id,
        source="manual", # Cumplimiento de la HU Dual
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
def get_expenses_summary(
    period_type: str = "monthly", 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Calcula el total de gastos y el desglose porcentual por categoría."""
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    # Buscar todos los gastos del período (manuales y automáticos)
    expenses = db.query(models.Expense).filter(
        models.Expense.business_id == business.id, 
        models.Expense.period_type == period_type
    ).all()

    total_amount = sum(e.amount for e in expenses)
    
    if total_amount == 0:
        return {"total_period_amount": 0.0, "categories_breakdown": []}

    # Agrupar sumando por categoría
    category_totals = {}
    for expense in expenses:
        # Buscamos el nombre de la categoría usando la relación
        cat_name = expense.category.name if expense.category else "Sin Categoría"
        if cat_name not in category_totals:
            category_totals[cat_name] = 0.0
        category_totals[cat_name] += expense.amount

    # Construir el desglose con porcentajes
    breakdown = []
    for name, amount in category_totals.items():
        percentage = (amount / total_amount) * 100
        breakdown.append({
            "category_name": name,
            "total_amount": amount,
            "percentage": round(percentage, 2)
        })

    # Ordenar de mayor gasto a menor gasto
    breakdown.sort(key=lambda x: x["total_amount"], reverse=True)

    return {
        "total_period_amount": total_amount,
        "categories_breakdown": breakdown
    }
    

# ==========================================
# ENDPOINTS PARA CATÁLOGO E INVENTARIO
# ==========================================

@app.post("/products", response_model=schemas.ProductResponse)
def create_product(
    product_data: schemas.ProductCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Crea un nuevo producto en el catálogo validando que el SKU sea único para la empresa."""
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    # Validación estricta: El SKU no se puede repetir en la misma empresa
    existing_product = db.query(models.Product).filter(
        models.Product.business_id == business.id,
        models.Product.sku == product_data.sku
    ).first()
    
    if existing_product:
        raise HTTPException(status_code=400, detail="Ya existe un producto registrado con este SKU.")

    new_product = models.Product(
        business_id=business.id,
        **product_data.model_dump() # Usar .dict() si usas Pydantic v1
    )
    
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    
    return new_product

@app.get("/products", response_model=List[schemas.ProductResponse])
def get_products(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Obtiene la lista completa de productos del negocio."""
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    products = db.query(models.Product).filter(models.Product.business_id == business.id).all()
    return products

@app.put("/products/{product_id}", response_model=schemas.ProductResponse)
def update_product(
    product_id: int,
    product_data: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Actualiza los datos de un producto existente."""
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.business_id == business.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Si se está intentando cambiar el SKU, debemos validar que el nuevo SKU no esté ocupado
    if product_data.sku and product_data.sku != product.sku:
        existing_product = db.query(models.Product).filter(
            models.Product.business_id == business.id,
            models.Product.sku == product_data.sku
        ).first()
        if existing_product:
            raise HTTPException(status_code=400, detail="El nuevo SKU ya está en uso por otro producto.")

    # Actualización dinámica: Solo modifica los campos que se enviaron en la petición
    update_data = product_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product

@app.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Elimina un producto físicamente de la base de datos."""
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.business_id == business.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    db.delete(product)
    db.commit()
    return {"message": "Producto eliminado exitosamente"}

@app.patch("/products/{product_id}/status", response_model=schemas.ProductResponse)
def toggle_product_status(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Activa o desactiva un producto sin eliminarlo de la base de datos (Soft Delete)."""
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.business_id == business.id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Invierte el estado actual
    product.is_active = not product.is_active
    
    db.commit()
    db.refresh(product)
    return product


# ==========================================
# ENDPOINTS DE VENTAS (POS)
# ==========================================

@app.post("/sales/pos")
def create_pos_sale(
    sale_data: schemas.SaleCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Procesa una venta múltiple desde el POS y descuenta stock automáticamente."""
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    if not sale_data.details:
        raise HTTPException(status_code=400, detail="El carrito de compras está vacío.")

    # 1. Crear la Cabecera de la Venta (Llenando tus campos obligatorios)
    total_sale = 0.0
    new_sale = models.Sale(
        business_id=business.id,
        source="pos", # Identificamos que viene del sistema de caja
        amount=0.0,   # Se actualizará al final
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

    # 2. Procesar el Carrito y Descontar Stock
    for item in sale_data.details:
        product = db.query(models.Product).filter(
            models.Product.id == item.product_id,
            models.Product.business_id == business.id
        ).with_for_update().first() 

        if not product:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Producto no encontrado.")
        
        if product.stock < item.quantity:
            db.rollback()
            raise HTTPException(
                status_code=400, 
                detail=f"Stock insuficiente para: {product.name}. Disponible: {product.stock}"
            )

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

    # 3. Guardar Total Real
    new_sale.amount = total_sale
    db.commit()
    
    return {
        "message": "Venta procesada con éxito", 
        "sale_id": new_sale.id, 
        "total": total_sale
    }
    
# ==========================================
# ENDPOINTS DEL DASHBOARD (ÉPICA 15)
# ==========================================

@app.get("/api/dashboard/financial")
def get_dashboard_financial(
    period: str = "this_month",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    # CORRECCIÓN: Sumamos el 'subtotal' de los detalles de venta en lugar de buscar 'total' en Sale
    total_income = db.query(func.sum(models.SaleDetail.subtotal)) \
        .join(models.Sale, models.SaleDetail.sale_id == models.Sale.id) \
        .filter(models.Sale.business_id == business.id).scalar() or 0.0

    # Sumar Egresos Reales
    total_expenses = db.query(func.sum(models.Expense.amount)).filter(models.Expense.business_id == business.id).scalar() or 0.0

    # Calcular Flujo de Caja Real
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
def get_dashboard_operational(
    period: str = "this_month",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # CORREGIDO: Cambiado owner_id por user_id
    business = db.query(models.Business).filter(models.Business.user_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Negocio no encontrado")

    # 1. Alertas reales de stock (Productos que bajaron de su stock mínimo)
    low_stock_alerts = db.query(models.Product).filter(
        models.Product.business_id == business.id,
        models.Product.stock <= models.Product.min_stock
    ).count()

    # 2. Unidades vendidas reales (Hoy)
    today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
    units_sold_today = db.query(func.sum(models.SaleDetail.quantity)) \
        .join(models.Sale, models.SaleDetail.sale_id == models.Sale.id) \
        .filter(
            models.Sale.business_id == business.id,
            models.Sale.created_at >= today_start
        ).scalar() or 0

    # 3. Top 5 Productos Reales más vendidos
    top_sales = db.query(
        models.Product.name,
        func.sum(models.SaleDetail.quantity).label('total_sold'),
        func.sum(models.SaleDetail.subtotal).label('total_revenue')
    ).join(models.SaleDetail, models.Product.id == models.SaleDetail.product_id) \
     .join(models.Sale, models.SaleDetail.sale_id == models.Sale.id) \
     .filter(models.Sale.business_id == business.id) \
     .group_by(models.Product.id, models.Product.name) \
     .order_by(func.sum(models.SaleDetail.quantity).desc()) \
     .limit(5).all()

    top_products = [
        {"name": item.name, "sold": int(item.total_sold), "revenue": float(item.total_revenue)}
        for item in top_sales
    ]

    return {
        "units_sold_today": int(units_sold_today),
        "low_stock_alerts": low_stock_alerts,
        "active_branches": 1,
        "top_products": top_products
    }