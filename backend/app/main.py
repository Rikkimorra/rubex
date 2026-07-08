from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.db import Base, engine
from app.routers import auth, listings, payments

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RUBex")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Mini App грузится из Telegram WebView — упрощаем CORS
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(payments.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Раздаём статику Mini App (webapp/) как корень сайта.
WEBAPP_DIR = Path(__file__).resolve().parent.parent.parent / "webapp"
if WEBAPP_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEBAPP_DIR), html=True), name="webapp")
