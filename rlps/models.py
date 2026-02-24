from sqlalchemy import Column, Integer, String, Float, Date
from database import Base

class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String, index=True)
    phone = Column(String)
    email = Column(String)
    amount = Column(Float)
    date_sent = Column(Date)
    followup_date = Column(Date)
    status = Column(String, default="Open")  # Open / Won / Lost
