"""Check PostgreSQL tables"""
from database import engine, DATABASE_AVAILABLE
from sqlalchemy import inspect

print("=" * 60)
print("POSTGRESQL TABLO KONTROLU")
print("=" * 60)
print(f"Baglanti Durumu: {'OK' if DATABASE_AVAILABLE else 'HATA'}")
if engine:
    print(f"Database URL: {engine.url}")
print()

if DATABASE_AVAILABLE and engine:
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Toplam Tablo Sayisi: {len(tables)}")
    print()
    print("Tablolar:")
    for i, table in enumerate(tables, 1):
        print(f"  {i}. {table}")
        columns = inspector.get_columns(table)
        print(f"     Kolon sayisi: {len(columns)}")
        # Show first few columns
        for col in columns[:3]:
            print(f"       - {col['name']} ({col['type']})")
        if len(columns) > 3:
            print(f"       ... ve {len(columns) - 3} kolon daha")
        print()
else:
    print("[HATA] Veritabani baglantisi yok!")

print("=" * 60)

