from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.bot.handlers import process_incoming_message
from app.services.client_service import get_dashboard_stats, list_clients
from app.services.meta_ads import MetaAdsService
from app.models import Client, CampaignInsight
from app.config import get_settings

settings = get_settings()
router = APIRouter()
templates = Jinja2Templates(directory="templates")
meta_service = MetaAdsService()


# ==================== WEBHOOK ULTRAMSG ====================

@router.post("/webhook")
async def ultramsg_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Endpoint que recebe mensagens do Ultramsg."""
    try:
        payload = await request.json()
        print(f"[Webhook] Recebido: {payload}")
        result = await process_incoming_message(db, payload)
        return {"status": "ok", "result": result}
    except Exception as e:
        print(f"[Webhook Error] {e}")
        return {"status": "error", "detail": str(e)}


@router.get("/webhook")
async def webhook_verify():
    """Alguns provedores fazem GET para verificar o endpoint."""
    return {"status": "Smart Assistant webhook active"}


# ==================== DASHBOARD ====================

@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, db: AsyncSession = Depends(get_db)):
    stats = await get_dashboard_stats(db)
    clients = await list_clients(db, limit=20)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "clients": clients,
            "company_name": settings.company_name,
        },
    )


@router.get("/clients", response_class=HTMLResponse)
async def clients_page(
    request: Request,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    clients = await list_clients(db, status=status, limit=100)
    return templates.TemplateResponse(
        "clients.html",
        {
            "request": request,
            "clients": clients,
            "status_filter": status,
            "company_name": settings.company_name,
        },
    )


@router.get("/client/{phone}", response_class=HTMLResponse)
async def client_detail(request: Request, phone: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client).where(Client.phone == phone))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return templates.TemplateResponse(
        "client_detail.html",
        {
            "request": request,
            "client": client,
            "company_name": settings.company_name,
        },
    )


# ==================== META ADS ====================

@router.get("/ads", response_class=HTMLResponse)
async def ads_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CampaignInsight).order_by(desc(CampaignInsight.created_at)).limit(20)
    )
    insights = result.scalars().all()
    recommendations = meta_service.generate_recommendations(
        [
            {
                "campaign_name": i.campaign_name,
                "ctr": i.ctr,
                "spend": i.spend,
                "clicks": i.clicks,
            }
            for i in insights
        ]
    )
    return templates.TemplateResponse(
        "ads.html",
        {
            "request": request,
            "insights": insights,
            "recommendations": recommendations,
            "is_configured": meta_service.is_configured(),
            "company_name": settings.company_name,
        },
    )


@router.post("/ads/sync")
async def sync_ads(db: AsyncSession = Depends(get_db)):
    if not meta_service.is_configured():
        raise HTTPException(status_code=400, detail="Meta Ads não configurado no .env")
    count = await meta_service.sync_insights_to_db(db)
    return RedirectResponse(url="/ads", status_code=303)


# ==================== API JSON (para futuras expansões) ====================

@router.get("/api/stats")
async def api_stats(db: AsyncSession = Depends(get_db)):
    return await get_dashboard_stats(db)


@router.get("/api/clients")
async def api_clients(status: str | None = None, db: AsyncSession = Depends(get_db)):
    clients = await list_clients(db, status=status)
    return [
        {
            "id": c.id,
            "phone": c.phone,
            "name": c.name,
            "company_name": c.company_name,
            "status": c.status,
            "package_bought": c.package_bought,
            "score": c.score,
            "last_interaction": c.last_interaction.isoformat() if c.last_interaction else None,
        }
        for c in clients
    ]


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "Smart Assistant Bot"}
