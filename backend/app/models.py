from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
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