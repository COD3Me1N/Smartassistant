from datetime import datetime
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Client, ConversationMessage, ClientStatus
from app.schemas import ClientUpdate


async def get_or_create_client(db: AsyncSession, phone: str) -> Client:
    phone_clean = phone.replace("@c.us", "").replace("+", "").strip()
    result = await db.execute(select(Client).where(Client.phone == phone_clean))
    client = result.scalar_one_or_none()

    if not client:
        client = Client(phone=phone_clean, status=ClientStatus.LEAD.value)
        db.add(client)
        await db.commit()
        await db.refresh(client)
    return client


async def update_client(db: AsyncSession, phone: str, data: dict) -> Client:
    client = await get_or_create_client(db, phone)

    for key, value in data.items():
        if value is not None and hasattr(client, key):
            setattr(client, key, value)

    client.last_interaction = datetime.utcnow()
    client.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(client)
    return client


async def save_message(db: AsyncSession, phone: str, role: str, content: str):
    phone_clean = phone.replace("@c.us", "").replace("+", "").strip()
    msg = ConversationMessage(phone=phone_clean, role=role, content=content)
    db.add(msg)

    # Incrementa contador de mensagens do cliente
    result = await db.execute(select(Client).where(Client.phone == phone_clean))
    client = result.scalar_one_or_none()
    if client:
        client.message_count += 1
        client.last_interaction = datetime.utcnow()

    await db.commit()


async def get_conversation_history(db: AsyncSession, phone: str, limit: int = 20) -> list[dict]:
    phone_clean = phone.replace("@c.us", "").replace("+", "").strip()
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.phone == phone_clean)
        .order_by(desc(ConversationMessage.created_at))
        .limit(limit)
    )
    messages = result.scalars().all()
    # Retorna em ordem cronológica
    return [{"role": m.role, "content": m.content} for m in reversed(messages)]


async def get_dashboard_stats(db: AsyncSession) -> dict:
    total = await db.scalar(select(func.count(Client.id)))
    clients = await db.scalar(
        select(func.count(Client.id)).where(Client.status == "cliente")
    )
    lost = await db.scalar(
        select(func.count(Client.id)).where(Client.status == "perdido")
    )
    leads = await db.scalar(
        select(func.count(Client.id)).where(Client.status.in_(["lead", "qualified", "proposta"]))
    )

    conversion_rate = round((clients / total * 100) if total else 0, 1)

    # Por pacote
    by_package = {}
    for pkg in ["basico", "business", "pro", "none"]:
        count = await db.scalar(
            select(func.count(Client.id)).where(Client.package_bought == pkg)
        )
        by_package[pkg] = count or 0

    # Por status
    by_status = {}
    for st in ["lead", "qualified", "proposta", "cliente", "perdido"]:
        count = await db.scalar(
            select(func.count(Client.id)).where(Client.status == st)
        )
        by_status[st] = count or 0

    # Motivos de perda
    result = await db.execute(
        select(Client.reason_not_bought, func.count(Client.id))
        .where(Client.status == "perdido", Client.reason_not_bought.isnot(None))
        .group_by(Client.reason_not_bought)
        .order_by(desc(func.count(Client.id)))
        .limit(5)
    )
    top_reasons = [{"reason": r[0], "count": r[1]} for r in result.all()]

    # Interações recentes
    result = await db.execute(
        select(Client)
        .order_by(desc(Client.last_interaction))
        .limit(10)
    )
    recent = [
        {
            "phone": c.phone,
            "name": c.name,
            "company_name": c.company_name,
            "status": c.status,
            "last_interaction": c.last_interaction.isoformat() if c.last_interaction else None,
        }
        for c in result.scalars().all()
    ]

    return {
        "total_leads": leads or 0,
        "total_clients": clients or 0,
        "total_lost": lost or 0,
        "total": total or 0,
        "conversion_rate": conversion_rate,
        "by_package": by_package,
        "by_status": by_status,
        "top_reasons_lost": top_reasons,
        "recent_interactions": recent,
    }


async def list_clients(db: AsyncSession, status: str | None = None, limit: int = 50):
    query = select(Client).order_by(desc(Client.last_interaction)).limit(limit)
    if status:
        query = query.where(Client.status == status)
    result = await db.execute(query)
    return result.scalars().all()
