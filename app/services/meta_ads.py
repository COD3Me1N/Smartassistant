"""
Serviço de análise de campanhas Meta Ads.
Usa a Graph API diretamente via httpx (mais leve que o SDK completo).
"""
import json
from datetime import datetime
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.models import CampaignInsight

settings = get_settings()


class MetaAdsService:
    def __init__(self):
        self.access_token = settings.meta_access_token
        self.ad_account_id = settings.meta_ad_account_id
        self.base_url = "https://graph.facebook.com/v21.0"

    def is_configured(self) -> bool:
        return bool(self.access_token and self.ad_account_id)

    async def get_campaigns_insights(self, date_preset: str = "last_30d") -> list[dict]:
        if not self.is_configured():
            return []

        url = f"{self.base_url}/{self.ad_account_id}/insights"
        params = {
            "access_token": self.access_token,
            "level": "campaign",
            "fields": "campaign_id,campaign_name,impressions,clicks,spend,actions,ctr,cpc",
            "date_preset": date_preset,
            "limit": 50,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(url, params=params)
                data = resp.json()
                if "error" in data:
                    print(f"[Meta Ads Error] {data['error']}")
                    return []
                return data.get("data", [])
            except Exception as e:
                print(f"[Meta Ads Exception] {e}")
                return []

    async def sync_insights_to_db(self, db: AsyncSession, date_preset: str = "last_30d") -> int:
        insights = await self.get_campaigns_insights(date_preset)
        count = 0

        for item in insights:
            campaign_id = item.get("campaign_id", "")
            actions = item.get("actions", [])
            leads = 0
            conversions = 0
            for action in actions:
                if action.get("action_type") in ("lead", "onsite_conversion.lead_grouped"):
                    leads += int(action.get("value", 0))
                if action.get("action_type") in ("purchase", "omni_purchase", "offsite_conversion.fb_pixel_purchase"):
                    conversions += int(action.get("value", 0))

            spend = float(item.get("spend", 0) or 0)
            cpl = round(spend / leads, 2) if leads > 0 else 0.0

            insight = CampaignInsight(
                campaign_id=campaign_id,
                campaign_name=item.get("campaign_name"),
                impressions=int(item.get("impressions", 0) or 0),
                clicks=int(item.get("clicks", 0) or 0),
                spend=spend,
                leads=leads,
                conversions=conversions,
                ctr=float(item.get("ctr", 0) or 0),
                cpc=float(item.get("cpc", 0) or 0),
                cpl=cpl,
                date_start=item.get("date_start"),
                date_stop=item.get("date_stop"),
                raw_data=json.dumps(item),
            )
            db.add(insight)
            count += 1

        await db.commit()
        return count

    def generate_recommendations(self, insights: list[dict]) -> list[str]:
        """Gera recomendações simples baseadas nos dados."""
        recommendations = []

        if not insights:
            return ["Nenhuma campanha encontrada. Configure o token e ad_account_id no .env"]

        for item in insights:
            name = item.get("campaign_name", "Campanha")
            ctr = float(item.get("ctr", 0) or 0)
            spend = float(item.get("spend", 0) or 0)
            clicks = int(item.get("clicks", 0) or 0)

            if ctr < 1.0 and spend > 50:
                recommendations.append(
                    f"⚠️ {name}: CTR baixo ({ctr:.2f}%). Considere testar novos criativos ou públicos."
                )
            if clicks > 0 and spend / clicks > 15:  # CPC alto em MT (ajuste conforme realidade)
                recommendations.append(
                    f"💰 {name}: CPC elevado. Revise segmentação e relevância do anúncio."
                )

        if not recommendations:
            recommendations.append("✅ Campanhas parecem saudáveis. Continue monitorando e testando.")

        return recommendations
