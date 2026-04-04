from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# CONFIGURACIÓN DE BASE DE DATOS (Conectado a tu contenedor Docker)
SQLALCHEMY_DATABASE_URL = "postgresql://kroot_admin:kroot_password@localhost:5433/kroot_db"

# INICIALIZACIÓN DEL MOTOR Y SESIÓN
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# DEPENDENCIA DE CONEXIÓN
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()