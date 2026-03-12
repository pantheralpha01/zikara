"""
Run this script once to create an admin user for testing.
Usage: python seed_admin.py
"""
import sys
sys.path.insert(0, ".")

import app.db.init_models  # noqa: F401 — registers all models with SQLAlchemy
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import hash_password, create_access_token, create_refresh_token

EMAIL = "admin@zikara.com"
PASSWORD = "Admin@1234"
FULL_NAME = "Zikara Admin"
PHONE = "0700000000"

db = SessionLocal()

existing = db.query(User).filter(User.email == EMAIL).first()
if existing:
    print(f"Admin already exists: {EMAIL}")
    db.close()
    sys.exit(0)

admin = User(
    full_name=FULL_NAME,
    email=EMAIL,
    password_hash=hash_password(PASSWORD),
    phone=PHONE,
    role="admin",
    status="active",
)
db.add(admin)
db.commit()
db.refresh(admin)

# Set refresh token so session is valid
refresh = create_refresh_token(str(admin.id), "admin")
admin.refresh_token = refresh
db.commit()

token = create_access_token(str(admin.id), "admin")

print("=" * 40)
print("Admin user created successfully!")
print(f"  Email   : {EMAIL}")
print(f"  Password: {PASSWORD}")
print(f"  Role    : admin")
print(f"  ID      : {admin.id}")
print("=" * 40)
print(f"\nAccess token (for Swagger Authorize):\n{token}")

db.close()
