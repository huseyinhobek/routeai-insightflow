"""
Database connection and session management
Supports PostgreSQL with SQLite fallback
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings
import os

# Base class for models
Base = declarative_base()

# Database configuration
DATABASE_AVAILABLE = False
engine = None
SessionLocal = None

def init_database():
    """Initialize database connection"""
    global engine, SessionLocal, DATABASE_AVAILABLE
    
    try:
        # Try PostgreSQL first
        if settings.DATABASE_URL and settings.DATABASE_URL.startswith('postgresql'):
            engine = create_engine(
                settings.DATABASE_URL,
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,   # Recycle connections after 1 hour
                pool_size=5,         # Number of connections to maintain
                max_overflow=10,     # Max connections beyond pool_size
                echo=settings.DEBUG,
                connect_args={
                    "connect_timeout": 10,
                    "keepalives": 1,
                    "keepalives_idle": 30,
                    "keepalives_interval": 10,
                    "keepalives_count": 5
                }
            )
            # Test connection
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("[OK] PostgreSQL baglantisi basarili")
            DATABASE_AVAILABLE = True
        else:
            # Fallback to SQLite
            sqlite_path = os.path.join(settings.UPLOAD_DIR, "sav_insight.db")
            os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
            engine = create_engine(
                f"sqlite:///{sqlite_path}",
                echo=settings.DEBUG
            )
            print(f"[OK] SQLite kullaniliyor: {sqlite_path}")
            DATABASE_AVAILABLE = True
            
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
    except Exception as e:
        print(f"[UYARI] Veritabani baglantisi basarisiz: {e}")
        print("[UYARI] In-memory mod kullanilacak (veriler yeniden baslatmada kaybolacak)")
        DATABASE_AVAILABLE = False

# Initialize on module load
init_database()


def get_db():
    """Dependency to get database session"""
    if not DATABASE_AVAILABLE or SessionLocal is None:
        # Return a dummy session that does nothing
        yield None
        return
        
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    if DATABASE_AVAILABLE and engine is not None:
        Base.metadata.create_all(bind=engine)

