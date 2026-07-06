from database import SessionLocal
from models import ProductivityRecord
from collections import Counter

db = SessionLocal()
try:
    rows = db.query(ProductivityRecord).all()
    print('total_records=', len(rows))
    counts = Counter(((r.status or '').strip() for r in rows))
    for k,v in counts.items():
        print(repr(k), v)
finally:
    db.close()
