from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# CONFIGURACIÓN DE BASE DE DATOS
SQLALCHEMY_DATABASE_URL = "sqlite:///./plataforma.db" # Usamos SQLite para desarrollo local

# INICIALIZACIÓN DEL MOTOR Y SESIÓN
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# DEPENDENCIA DE CONEXIÓN
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()