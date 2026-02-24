from pydantic import BaseModel
from datetime import date

class QuotationCreate(BaseModel):
    client_name: str
    phone: str
    email: str
    amount: float
    date_sent: date
    followup_date: date

class QuotationResponse(QuotationCreate):
    id: int
    status: str

    class Config:
        from_attributes = True
