from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Date, UniqueConstraint, Text
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


# ==========================================
# TABLA DE VENTAS (INGRESOS MANUALES Y POS) 
# ==========================================   

class Sale(Base):
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("business.id", ondelete="CASCADE"), nullable=False)

    # ── Origen de la Venta ─────────
    source          = Column(String, default="manual", nullable=False) # 'manual' o 'pos'

    # ── Campos originales ──────────────────────────────────
    amount          = Column(Float,   nullable=False) # Será el Total de la factura
    period_type     = Column(String,  nullable=False)   # 'monthly' | 'weekly'
    period_date     = Column(Date,    nullable=False)
    category        = Column(String,  nullable=True)
    payment_method  = Column(String,  nullable=True)
    description     = Column(String,  nullable=True)

    # ── Datos del cliente (CRM Futuro) ─────────────────────
    client_name     = Column(String,  nullable=True)
    client_type     = Column(String,  nullable=True)    
    client_contact  = Column(String,  nullable=True)    
    client_document = Column(String,  nullable=True)    

    # ── Detalle del producto (Para Ingresos Manuales) ───────────
    product_name    = Column(String,  nullable=True)
    quantity        = Column(Float,   nullable=True)    
    unit_price      = Column(Float,   nullable=True)

    # ── Información financiera ─────────────────────────────
    payment_status  = Column(String,  nullable=True)    
    invoice_ref     = Column(String,  nullable=True)    

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    business   = relationship("Business", backref="sales")
    
    # ── NUEVO: RELACIÓN POS ─────────────────────────────
    # Esto permite que una venta tenga múltiples productos asociados
    details = relationship("SaleDetail", back_populates="sale", cascade="all, delete-orphan")


# ── TABLA PARA SOPORTAR MÚLTIPLES PRODUCTOS EN EL POS ──
class SaleDetail(Base):
    __tablename__ = "sale_details"
    
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    sale = relationship("Sale", back_populates="details")
    product = relationship("Product")
        

# ==========================================
# MODELOS DE GASTOS OPERATIVOS
# ==========================================

class ExpenseCategory(Base):
    __tablename__ = "expense_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    # Si business_id es nulo, es una categoría global/predefinida de Kroot.
    # Si tiene un ID, es una categoría personalizada creada por esa empresa.
    business_id = Column(Integer, ForeignKey("business.id", ondelete="CASCADE"), nullable=True)
    
    name = Column(String, nullable=False)
    is_default = Column(Boolean, default=False)

    business = relationship("Business", backref="custom_categories")


class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("business.id", ondelete="CASCADE"), nullable=False)
    
    # ── Relación con la categoría ──────────────────────────
    category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=False)
    
    # ── Origen del Gasto (HU Dual) ─────────────────────────
    source = Column(String, default="manual", nullable=False) # 'manual' o 'purchase'

    # ── Campos financieros ─────────────────────────────────
    amount = Column(Float, nullable=False)
    period_type = Column(String, nullable=False)   # 'monthly' | 'weekly'
    period_date = Column(Date, nullable=False)
    
    # ── Detalles adicionales ───────────────────────────────
    supplier_name = Column(String, nullable=True)  # A quién se le pagó
    description = Column(String, nullable=True)    # Concepto del gasto
    receipt_ref = Column(String, nullable=True)    # N° de factura/recibo de pago

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    business = relationship("Business", backref="expenses")
    category = relationship("ExpenseCategory")

    
# ==========================================
# MODELOS DE CATÁLOGO E INVENTARIO 
# ==========================================

class ProductCategory(Base):
    __tablename__ = "product_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    # business_id en Null permite crear categorías globales por defecto (ej. 'General')
    business_id = Column(Integer, ForeignKey("business.id", ondelete="CASCADE"), nullable=True)
    
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_default = Column(Boolean, default=False)

    business = relationship("Business", backref="product_categories")


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("business.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=True)
    
    # ── Identificación ─────────────────────────────────────
    name = Column(String, nullable=False)
    sku = Column(String, index=True, nullable=False)
    barcode = Column(String, index=True, nullable=True)
    description = Column(Text, nullable=True)
    
    # ── Precios y Medidas ──────────────────────────────────
    sale_price = Column(Float, nullable=False)
    cost_price = Column(Float, nullable=False)
    unit = Column(String, default="unidad", nullable=False) # Ej: unidad, kg, litro, paquete
    
    # ── Configuración y Estado ─────────────────────────────
    image_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    min_stock = Column(Float, default=5.0) # Nivel para disparar alertas
    stock = Column(Float, default=0.0) # Stock actual, se actualizará con ventas e ingresos de inventario
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    business = relationship("Business", backref="products")
    category = relationship("ProductCategory")

    # ── Restricciones ──────────────────────────────────────
    # Garantiza que el SKU sea único POR EMPRESA, no a nivel global
    __table_args__ = (
        UniqueConstraint('business_id', 'sku', name='_business_sku_uc'),
    )