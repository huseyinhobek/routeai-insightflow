"""
Migration script to add pgvector extension
This should be run before creating tables that use vector columns
"""
from sqlalchemy import text
from database import engine, DATABASE_AVAILABLE


def upgrade():
    """Add pgvector extension to PostgreSQL database"""
    if not DATABASE_AVAILABLE or engine is None:
        print("[UYARI] Database not available, skipping pgvector extension")
        return
    
    try:
        with engine.connect() as conn:
            # Create extension if not exists (requires superuser privileges)
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("[OK] pgvector extension added successfully")
    except Exception as e:
        # If permission denied or extension already exists, that's okay
        if "permission denied" in str(e).lower() or "already exists" in str(e).lower():
            print(f"[INFO] pgvector extension check: {e}")
        else:
            print(f"[UYARI] Could not add pgvector extension: {e}")
            print("[UYARI] You may need to install pgvector manually or grant permissions")


def downgrade():
    """Remove pgvector extension (not recommended in production)"""
    if not DATABASE_AVAILABLE or engine is None:
        return
    
    try:
        with engine.connect() as conn:
            conn.execute(text("DROP EXTENSION IF EXISTS vector"))
            conn.commit()
            print("[OK] pgvector extension removed")
    except Exception as e:
        print(f"[UYARI] Could not remove pgvector extension: {e}")


if __name__ == "__main__":
    upgrade()

