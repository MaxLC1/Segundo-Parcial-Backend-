from app.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
db.execute(text("UPDATE alembic_version SET version_num = '2db956f448fa'"))
db.commit()
print('Alembic version restored')
