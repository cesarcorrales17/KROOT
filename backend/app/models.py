from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base

# MODELO DE TABLA USUARIOS
class User(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # REGLAS DE NEGOCIO Y SEGURIDAD (Las que ya tenías)
    is_active = Column(Boolean, default=True)      # Estado del usuario
    failed_attempts = Column(Integer, default=0)   # Contador de intentos fallidos
    locked_until = Column(DateTime, nullable=True) # Tiempo de bloqueo por 15 min

    # NUEVO: REGLAS DEL REGISTRO Y WIZARD
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())