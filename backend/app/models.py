from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# MODELO DE TABLA USUARIOS
class User(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # REGLAS DE NEGOCIO Y SEGURIDAD
    is_active = Column(Boolean, default=True)      # Estado del usuario
    failed_attempts = Column(Integer, default=0)   # Contador de intentos fallidos
    locked_until = Column(DateTime, nullable=True) # Tiempo de bloqueo por 15 min

    # REGLAS DEL REGISTRO Y WIZARD
    is_verified = Column(Boolean, default=False)
    is_setup_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relación uno a uno con Business (un usuario tiene una empresa, una empresa pertenece a un usuario)
    business = relationship("Business", back_populates="user", uselist=False, cascade="all, delete-orphan")

# TABLA PARA TOKENS DE RECUPERACIÓN DE CONTRASEÑA
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    # ondelete="CASCADE" significa que si borras un usuario, sus tokens se borran solos
    user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relación para poder consultar user.password_reset_tokens fácilmente
    user = relationship("User")
    
# NUEVO: TABLA DE CONFIGURACIÓN DE LA EMPRESA (WIZARD)
class Business(Base):
    __tablename__ = "business"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Paso 1 - Información básica
    business_name = Column(String, nullable=True)
    business_type = Column(String, nullable=True)
    
    # Paso 2 - Información financiera
    industry = Column(String, nullable=True)
    
    # Paso 3 - Información adicional 
    business_size = Column(String, nullable=True)
    currency = Column(String, default="COP")
    
    # Paso 4 - Estimaciones financieras
    estimated_income = Column(Integer, nullable=True) # Usamos Integer para simplificar, o Float si prefieres decimales
    estimated_expenses = Column(Integer, nullable=True)
    
    # Paso 5 - Configuración de seguimiento
    tracking_frequency = Column(String, nullable=True)
    
    # Control del Wizard 
    onboarding_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) # Se actualiza solo en cada "auto-guardado"

    user = relationship("User", back_populates="business")
    
    
# TABLA DE TRANSACCIONES (INGRESOS Y GASTOS)
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    # ondelete="CASCADE" significa que si borras una empresa, sus transacciones se borran solas
    business_id = Column(Integer, ForeignKey("business.id", ondelete="CASCADE"), nullable=False)
    
    transaction_type = Column(String, nullable=False) # 'ingreso' o 'gasto'
    amount = Column(Float, nullable=False)
    transaction_date = Column(Date, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relación (Asegurar que la clase Business la reconozca después)
    business = relationship("Business", backref="transactions")
    
class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("business.id", ondelete="CASCADE"), nullable=False)

    # ── Campos originales ──────────────────────────────────────────────────
    amount          = Column(Float,   nullable=False)
    period_type     = Column(String,  nullable=False)   # 'monthly' | 'weekly'
    period_date     = Column(Date,    nullable=False)
    category        = Column(String,  nullable=True)
    payment_method  = Column(String,  nullable=True)
    description     = Column(String,  nullable=True)

    # ── Datos del cliente ─────────────────────────────────────────────────
    client_name     = Column(String,  nullable=True)
    client_type     = Column(String,  nullable=True)    # 'Persona Natural', 'Empresa', etc.
    client_contact  = Column(String,  nullable=True)    # teléfono o email
    client_document = Column(String,  nullable=True)    # cédula / NIT

    # ── Detalle del producto/servicio ─────────────────────────────────────
    product_name    = Column(String,  nullable=True)
    quantity        = Column(Float,   nullable=True)    # Float para permitir fracciones
    unit_price      = Column(Float,   nullable=True)

    # ── Información financiera ────────────────────────────────────────────
    payment_status  = Column(String,  nullable=True)    # 'paid' | 'pending' | 'partial' | 'cancelled'
    invoice_ref     = Column(String,  nullable=True)    # número de factura / comprobante

    # ── Control y logística ───────────────────────────────────────────────
    sales_channel   = Column(String,  nullable=True)    # 'Presencial', 'WhatsApp', etc.
    internal_notes  = Column(String,  nullable=True)
    sale_time       = Column(String,  nullable=True)    # hora de la venta HH:MM

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    business   = relationship("Business", backref="sales")