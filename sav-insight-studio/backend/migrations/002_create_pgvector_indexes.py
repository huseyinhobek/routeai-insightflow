"""
Migration script to create pgvector HNSW indexes
Should be run after embeddings table is created
"""
from sqlalchemy import text
from database import engine, DATABASE_AVAILABLE


def upgrade():
    """Create HNSW indexes on embeddings.vector column"""
    if not DATABASE_AVAILABLE or engine is None:
        print("[UYARI] Database not available, skipping pgvector index creation")
        return
    
    try:
        with engine.connect() as conn:
            # First, we need to ensure the vector column is actually of type vector
            # If it was created as TEXT, we need to alter it
            # Check if column exists and is TEXT type
            check_sql = text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'embeddings' AND column_name = 'vector'
            """)
            
            result = conn.execute(check_sql).first()
            if result and result.data_type == 'text':
                # Alter column to vector type (if we have vectors stored as text, this needs migration)
                # For now, we'll create index assuming vector type
                # In production, you might want to add a migration step to convert TEXT to vector
                print("[INFO] Vector column is TEXT type, index creation may need vector type conversion first")
            
            # Create HNSW index for variable embeddings
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_embeddings_vector_variable_hnsw 
                    ON embeddings 
                    USING hnsw (vector vector_cosine_ops)
                    WHERE object_type = 'variable'
                """))
                conn.commit()
                print("[OK] HNSW index created for variable embeddings")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("[INFO] Variable embeddings HNSW index already exists")
                else:
                    print(f"[UYARI] Could not create variable embeddings index: {e}")
            
            # Create HNSW index for utterance embeddings
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_embeddings_vector_utterance_hnsw 
                    ON embeddings 
                    USING hnsw (vector vector_cosine_ops)
                    WHERE object_type = 'utterance'
                """))
                conn.commit()
                print("[OK] HNSW index created for utterance embeddings")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("[INFO] Utterance embeddings HNSW index already exists")
                else:
                    print(f"[UYARI] Could not create utterance embeddings index: {e}")
                    
    except Exception as e:
        print(f"[UYARI] Error creating pgvector indexes: {e}")
        print("[UYARI] You may need to ensure the vector column is of type 'vector' in PostgreSQL")


def downgrade():
    """Remove HNSW indexes"""
    if not DATABASE_AVAILABLE or engine is None:
        return
    
    try:
        with engine.connect() as conn:
            conn.execute(text("DROP INDEX IF EXISTS ix_embeddings_vector_variable_hnsw"))
            conn.execute(text("DROP INDEX IF EXISTS ix_embeddings_vector_utterance_hnsw"))
            conn.commit()
            print("[OK] pgvector indexes removed")
    except Exception as e:
        print(f"[UYARI] Could not remove pgvector indexes: {e}")


if __name__ == "__main__":
    upgrade()

