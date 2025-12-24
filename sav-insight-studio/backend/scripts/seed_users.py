#!/usr/bin/env python3
"""
Seed script to create initial organizations and users.
Run this script to set up test users and demo organizations.

Usage:
    python scripts/seed_users.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
import hashlib
from datetime import datetime
from database import SessionLocal, DATABASE_AVAILABLE, init_database
from models import Organization, User


def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_org(db, name: str, slug: str, settings: dict = None) -> Organization:
    """Create an organization if it doesn't exist"""
    existing = db.query(Organization).filter(Organization.slug == slug).first()
    if existing:
        print(f"  [EXISTS] Organization: {name} ({slug})")
        return existing
    
    org = Organization(
        id=str(uuid.uuid4()),
        name=name,
        slug=slug,
        settings=settings or {
            "export_allowed": True,
            "reviewer_can_export": False,
            "retention_days": 365,
        },
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    print(f"  [CREATED] Organization: {name} ({slug})")
    return org


def create_user(db, email: str, name: str, org: Organization, role: str, password: str = None) -> User:
    """Create a user if it doesn't exist"""
    existing = db.query(User).filter(User.email == email.lower()).first()
    
    # Default password if not provided
    if not password:
        password = "Native2024!"  # Default password for all users
    
    password_hash = hash_password(password)
    
    if existing:
        # Update org, role and password if changed
        existing.org_id = org.id
        existing.role = role
        existing.name = name
        existing.password_hash = password_hash
        db.commit()
        print(f"  [UPDATED] User: {email} -> {role} @ {org.name}")
        return existing
    
    user = User(
        id=str(uuid.uuid4()),
        email=email.lower(),
        name=name,
        org_id=org.id,
        role=role,
        status="active",
        password_hash=password_hash,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"  [CREATED] User: {email} ({role}) @ {org.name}")
    return user


def main():
    print("\n" + "="*60)
    print("SAV Insight Studio - User & Organization Seed Script")
    print("="*60 + "\n")
    
    # Initialize database
    init_database()
    
    if not DATABASE_AVAILABLE:
        print("[ERROR] Database not available. Cannot seed users.")
        sys.exit(1)
    
    db = SessionLocal()
    
    try:
        # =================================================================
        # 1. Create Native Organization (Internal Team)
        # =================================================================
        print("\n[1] Creating Native Organization...")
        native_org = create_org(
            db,
            name="Native",
            slug="native",
            settings={
                "export_allowed": True,
                "reviewer_can_export": True,
                "retention_days": 365,
            }
        )
        
        # =================================================================
        # 2. Create Native Team Users
        # =================================================================
        print("\n[2] Creating Native Team Users...")
        
        # Super Admin - full access
        create_user(db, "native-admin@nativeag.io", "Native Admin", native_org, "super_admin", password="Native2024!")
        
        # Team members - org_admin role for full org access
        native_users = [
            ("frank@nativeag.io", "Frank", "org_admin"),
            ("branden@nativeag.io", "Branden", "org_admin"),
            ("vincent@nativeag.io", "Vincent", "org_admin"),
            ("mike@nativeag.io", "Mike", "org_admin"),
            ("enes@nativeag.io", "Enes", "org_admin"),
            ("nesrin@nativeag.io", "Nesrin", "org_admin"),
            ("huseyin@nativeag.io", "Hüseyin", "org_admin"),
            ("fabian@nativeag.io", "Fabian", "org_admin"),
        ]
        
        for email, name, role in native_users:
            create_user(db, email, name, native_org, role)
        
        # =================================================================
        # 3. Create Demo Organizations
        # =================================================================
        print("\n[3] Creating Demo Organizations...")
        
        demo_org_1 = create_org(
            db,
            name="Demo Company 1",
            slug="demo-company-1",
            settings={
                "export_allowed": True,
                "reviewer_can_export": False,
                "retention_days": 90,
            }
        )
        
        demo_org_2 = create_org(
            db,
            name="Demo Company 2",
            slug="demo-company-2",
            settings={
                "export_allowed": True,
                "reviewer_can_export": True,
                "retention_days": 180,
            }
        )
        
        # =================================================================
        # 4. Create Demo Users
        # =================================================================
        print("\n[4] Creating Demo Users...")
        
        # Demo Company 1 users (using example.com which is RFC 2606 compliant)
        create_user(db, "admin@demo1.example.com", "Demo1 Admin", demo_org_1, "org_admin", "Demo123!")
        create_user(db, "transformer@demo1.example.com", "Demo1 Transformer", demo_org_1, "transformer", "Demo123!")
        create_user(db, "reviewer@demo1.example.com", "Demo1 Reviewer", demo_org_1, "reviewer", "Demo123!")
        create_user(db, "viewer@demo1.example.com", "Demo1 Viewer", demo_org_1, "viewer", "Demo123!")
        
        # Demo Company 2 users
        create_user(db, "admin@demo2.example.com", "Demo2 Admin", demo_org_2, "org_admin", "Demo123!")
        create_user(db, "transformer@demo2.example.com", "Demo2 Transformer", demo_org_2, "transformer", "Demo123!")
        create_user(db, "reviewer@demo2.example.com", "Demo2 Reviewer", demo_org_2, "reviewer", "Demo123!")
        create_user(db, "viewer@demo2.example.com", "Demo2 Viewer", demo_org_2, "viewer", "Demo123!")
        
        # =================================================================
        # Summary
        # =================================================================
        print("\n" + "="*60)
        print("SEED COMPLETE!")
        print("="*60)
        
        print("\n📋 Native Team Accounts:")
        print("-" * 40)
        print("  native-admin@nativeag.io  (Super Admin)")
        print("  frank@nativeag.io         (Org Admin)")
        print("  branden@nativeag.io       (Org Admin)")
        print("  vincent@nativeag.io       (Org Admin)")
        print("  mike@nativeag.io          (Org Admin)")
        print("  enes@native.dev           (Org Admin)")
        print("  nesrin@nativeag.io        (Org Admin)")
        print("  huseyin@nativeag.io       (Org Admin)")
        print("  fabian@nativeag.io        (Org Admin)")
        print("\n  🔑 Default Password: Native2024!")
        
        print("\n📋 Demo Company 1 Accounts (OTP disabled):")
        print("-" * 40)
        print("  admin@demo1.example.com         (Org Admin)")
        print("  transformer@demo1.example.com   (Transformer)")
        print("  reviewer@demo1.example.com      (Reviewer)")
        print("  viewer@demo1.example.com        (Viewer)")
        print("  🔑 Password: Demo123!")
        
        print("\n📋 Demo Company 2 Accounts (OTP disabled):")
        print("-" * 40)
        print("  admin@demo2.example.com         (Org Admin)")
        print("  transformer@demo2.example.com   (Transformer)")
        print("  reviewer@demo2.example.com      (Reviewer)")
        print("  viewer@demo2.example.com        (Viewer)")
        print("  🔑 Password: Demo123!")
        
        print("\n💡 Login Instructions:")
        print("-" * 40)
        print("  1. Go to https://n8n.n0ps.net/sav-insight/#/login")
        print("  2. Enter email + password (Native2024!)")
        print("  3. Check your email for 6-digit verification code")
        print("  4. Enter the code to complete login")
        print()
        
    except Exception as e:
        print(f"\n[ERROR] Seed failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

