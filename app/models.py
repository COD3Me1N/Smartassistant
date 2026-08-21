from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, DateTime, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
import enum


class ClientStatus(str, enum.Enum):
    LEAD = "lead"
    QUALIFIED = "qualified"
    PROPOSAL = "proposta"
    CLIENT = "cliente"
    LOST = "perdido"


class PackageType(str, enum.Enum):
    BASICO = "basico"
    BUSINESS = "business"
    PRO = "pro"
    NONE = "none"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    company_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # saúde, e-commerce, serviços...
    company_size: Mapped[str | None] = mapped_column(String(50), nullable=True)   # 1-5, 6-20, 21-50, 50+
    status: Mapped[str] = mapped_column(String(30), default=ClientStatus.LEAD.value)
    package_bought: Mapped[str] = mapped_column(String(30), default=PackageType.NONE.value)
    reason_not_bought: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0)  # 0-100 potencial
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # organico / meta_ads
    conversation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    last_interaction: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(30), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user / assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CampaignInsight(Base):
    __tablename__ = "campaign_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[str] = mapped_column(String(100))
    campaign_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    spend: Mapped[float] = mapped_column(Float, default=0.0)
    leads: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    ctr: Mapped[float] = mapped_column(Float, default=0.0)
    cpc: Mapped[float] = mapped_column(Float, default=0.0)
    cpl: Mapped[float] = mapped_column(Float, default=0.0)
    date_start: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date_stop: Mapped[str | None] = mapped_column(String(20), nullable=True)
    raw_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
