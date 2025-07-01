"""
Módulo de configuración de base de datos SQLAlchemy.

Este módulo configura la conexión a PostgreSQL usando SQLAlchemy,
maneja el pool de conexiones y proporciona la dependency para FastAPI.

Funcionalidades:
- Configuración de engine SQLAlchemy con pool optimizado
- Session factory para transacciones
- Dependency get_db() para inyección en FastAPI endpoints
- Logging de errores de conexión
- Soporte para testing con SQLite

Autor: Sistema SIFEN
Fecha: 2024
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .config import settings

# Configurar logging
logger = logging.getLogger(__name__)

# === CONFIGURACIÓN DEL ENGINE ===


def get_engine_config() -> dict:
    """
    Obtiene la configuración del engine según el ambiente.

    Returns:
        dict: Configuración del engine SQLAlchemy
    """
    config = {
        "echo": settings.DATABASE_ECHO,
        "pool_pre_ping": True,  # Verificar conexiones antes de usar
        "pool_recycle": 3600,   # Reciclar conexiones cada hora
    }

    # Configuración específica según el tipo de base de datos
    if settings.DATABASE_URL.startswith("sqlite"):
        # Para testing con SQLite
        config.update({
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False}
        })
    else:
        # Para PostgreSQL en producción/desarrollo
        config.update({
            "pool_size": 5,         # Conexiones en el pool
            "max_overflow": 10,     # Conexiones adicionales
            "pool_timeout": 30,     # Timeout para obtener conexión
        })

    return config


# Crear engine con configuración optimizada
engine = create_engine(settings.DATABASE_URL, **get_engine_config())

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base declarativa para modelos
Base = declarative_base()

# === EVENT LISTENERS ===


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Configura pragmas para SQLite (útil en testing).

    Args:
        dbapi_connection: Conexión DBAPI
        connection_record: Record de conexión
    """
    if 'sqlite' in settings.DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@event.listens_for(Engine, "engine_connect")
def log_connection(connection, branch):
    """
    Registra conexiones a la base de datos.

    Args:
        connection: Conexión SQLAlchemy
        branch: Branch info
    """
    logger.debug("Nueva conexión establecida a BD")

# === DEPENDENCY FUNCTIONS ===


def get_db() -> Generator[Session, None, None]:
    """
    Dependency para obtener sesión de base de datos en FastAPI.

    Maneja automáticamente:
    - Apertura de sesión
    - Cierre de sesión
    - Logging de errores

    Yields:
        Session: Sesión SQLAlchemy para operaciones de BD

    Raises:
        SQLAlchemyError: En caso de error de base de datos
    """
    db = SessionLocal()
    try:
        logger.debug("Sesión de BD iniciada")
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Error en operación de BD: {str(e)}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error inesperado en sesión BD: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
        logger.debug("Sesión de BD cerrada")


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager para operaciones de BD fuera de FastAPI.

    Uso:
        with get_db_context() as db:
            # operaciones con db
            pass

    Yields:
        Session: Sesión SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Error en context manager BD: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

# === UTILITY FUNCTIONS ===


def test_connection() -> bool:
    """
    Prueba la conexión a la base de datos.

    Returns:
        bool: True si la conexión es exitosa, False en caso contrario
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("✅ Conexión a BD exitosa")
        return True
    except Exception as e:
        logger.error(f"❌ Error de conexión a BD: {str(e)}")
        return False


def create_all_tables():
    """
    Crea todas las tablas definidas en los modelos.

    Nota: Solo usar en desarrollo/testing.
    En producción usar Alembic migrations.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tablas creadas exitosamente")
    except Exception as e:
        logger.error(f"❌ Error creando tablas: {str(e)}")
        raise


def drop_all_tables():
    """
    Elimina todas las tablas (solo para testing).

    ⚠️ PELIGROSO: Solo usar en testing
    """
    if not settings.ENVIRONMENT == "testing":
        raise RuntimeError("drop_all_tables solo permitido en testing")

    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("⚠️ Todas las tablas eliminadas")
    except Exception as e:
        logger.error(f"❌ Error eliminando tablas: {str(e)}")
        raise

# === HEALTH CHECK ===


def get_db_health() -> dict:
    """
    Verifica el estado de salud de la base de datos.

    Returns:
        dict: Estado de la BD con métricas básicas
    """
    try:
        with engine.connect() as connection:
            # Test básico de conexión
            result = connection.execute(text("SELECT 1")).scalar()

            # Información del pool (métodos seguros para SQLAlchemy 2.0+)
            pool = engine.pool
            pool_status = {
                "pool_size": getattr(pool, 'size', lambda: 'N/A')(),
                "checked_in": getattr(pool, 'checkedin', lambda: 'N/A')(),
                "checked_out": getattr(pool, 'checkedout', lambda: 'N/A')(),
                "overflow": getattr(pool, 'overflow', lambda: 'N/A')(),
            }

            return {
                "status": "healthy",
                "connection_test": result == 1,
                "database_url": settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else "SQLite",
                "pool_status": pool_status,
                "engine_echo": settings.DATABASE_ECHO
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "connection_test": False
        }
