from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.api.routes import router
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    print(f"🚀 {settings.company_name} Bot iniciado!")
    print(f"📡 Webhook: {settings.app_url}/webhook")
    yield
    # Shutdown
    print("👋 Bot encerrado.")


app = FastAPI(
    title=f"{settings.company_name} - Bot de Atendimento",
    description="Bot de vendas e retenção via WhatsApp + Painel + Meta Ads",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)

# Static files (se precisar de CSS/JS extras)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
