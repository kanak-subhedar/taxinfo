from sqlalchemy.orm import Session
from rlps.models import Quotation
from schemas import QuotationCreate

def create_quotation(db: Session, quotation: QuotationCreate):
    db_quotation = Quotation(**quotation.dict())
    db.add(db_quotation)
    db.commit()
    db.refresh(db_quotation)
    return db_quotation

def get_all_quotations(db: Session):
    return db.query(Quotation).all()

def get_pending_followups(db: Session):
    from datetime import date
    today = date.today()
    return db.query(Quotation).filter(
        Quotation.followup_date <= today,
        Quotation.status == "Open"
    ).all()
