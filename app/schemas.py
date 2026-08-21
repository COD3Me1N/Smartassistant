from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ClientBase(BaseModel):
    phone: str
    name: Optional[str] = None
    company_name: Optional[str] = None
    company_type: Optional[str] = None
    company_size: Optional[str] = None
    status: str = "lead"
    package_bought: str = "none"
    reason_not_bought: Optional[str] = None
    score: int = 0
    source: Optional[str] = None
    conversation_summary: Optional[str] = None
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    company_type: Optional[str] = None
    company_size: Optional[str] = None
    status: Optional[str] = None
    package_bought: Optional[str] = None
    reason_not_bought: Optional[str] = None
    score: Optional[int] = None
    source: Optional[str] = None
    conversation_summary: Optional[str] = None
    notes: Optional[str] = None


class ClientOut(ClientBase):
    id: int
    message_count: int
    last_interaction: datetime
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_leads: int
    total_clients: int
    total_lost: int
    conversion_rate: float
    by_package: dict
    by_status: dict
    top_reasons_lost: list
    recent_interactions: list
