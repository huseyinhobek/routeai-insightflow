"""
Test database connection and table creation
"""
import sys
from database import init_database, engine, Base, DATABASE_AVAILABLE
from models import Dataset, Variable, ExportHistory, AnalysisHistory

print("=" * 60)
print("PostgreSQL Baglanti Testi")
print("=" * 60)

# Initialize database
init_database()

if DATABASE_AVAILABLE and engine is not None:
    print("\n[OK] Veritabani baglantisi basarili!")
    print(f"[OK] Engine: {engine.url}")
    
    # Create tables
    print("\n[TABLO] Tablolar olusturuluyor...")
    try:
        Base.metadata.create_all(bind=engine)
        print("[OK] Tablolar basariyla olusturuldu!")
        
        # List tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\n[OK] Olusturulan tablolar ({len(tables)} adet):")
        for table in tables:
            print(f"  - {table}")
            
    except Exception as e:
        print(f"[HATA] Tablo olusturma hatasi: {e}")
        sys.exit(1)
else:
    print("\n[UYARI] Veritabani baglantisi basarisiz!")
    print("[UYARI] In-memory mod kullanilacak")
    sys.exit(1)

print("\n" + "=" * 60)
print("Test tamamlandi!")
print("=" * 60)

