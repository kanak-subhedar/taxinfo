from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date

import models
import crud
from database import engine, SessionLocal

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="rlps/templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    quotations = crud.get_all_quotations(db)
    pending = crud.get_pending_followups(db)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "quotations": quotations,
        "pending": pending
    })


@app.get("/add", response_class=HTMLResponse)
def add_form(request: Request):
    return templates.TemplateResponse("add_quotation.html", {"request": request})


@app.post("/add")
def add_quotation(
    client_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    amount: float = Form(...),
    date_sent: date = Form(...),
    followup_date: date = Form(...),
    db: Session = Depends(get_db)
):
    quotation_data = {
        "client_name": client_name,
        "phone": phone,
        "email": email,
        "amount": amount,
        "date_sent": date_sent,
        "followup_date": followup_date
    }

    crud.create_quotation(db, quotation_data)
    return RedirectResponse("/", status_code=303)
