from datetime import datetime, timedelta
import bcrypt
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Base, engine, SessionLocal
from models import User

SECRET_KEY = "change-this-to-a-long-random-string"
ALGORITHM = "HS256"

Base.metadata.create_all(bind=engine)
app = FastAPI(title="AgroVision AI")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class SignupData(BaseModel):
    name: str
    email: str
    password: str

class LoginData(BaseModel):
    email: str
    password: str

@app.get("/")
def root():
    return {"status": "running"}

@app.post("/signup")
def signup(data: SignupData, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")
    hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
    db.add(User(name=data.name, email=data.email, password=hashed))
    db.commit()
    return {"message": "Account created"}

@app.post("/login")
def login(data: LoginData, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not bcrypt.checkpw(data.password.encode(), user.password.encode()):
        raise HTTPException(401, "Invalid email or password")
    token = jwt.encode({"sub": user.email,
                        "exp": datetime.utcnow() + timedelta(hours=12)},
                       SECRET_KEY, algorithm=ALGORITHM)
    return {"token": token, "name": user.name}