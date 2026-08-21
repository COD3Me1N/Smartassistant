import httpx
from app.config import get_settings

settings = get_settings()


class UltramsgClient:
    def __init__(self):
        self.instance_id = settings.ultramsg_instance_id
        self.token = settings.ultramsg_token
        self.base_url = f"https://api.ultramsg.com/{self.instance_id}"

    async def send_message(self, to: str, body: str, priority: int = 10) -> dict:
        """Envia mensagem de texto via Ultramsg."""
        # Remove @c.us se presente e garante formato correto
        to_clean = to.replace("@c.us", "").replace("+", "").strip()
        if not to_clean.startswith("258") and len(to_clean) <= 9:
            # Assume Moçambique se número curto
            to_clean = "258" + to_clean

        url = f"{self.base_url}/messages/chat"
        payload = {
            "token": self.token,
            "to": to_clean,
            "body": body,
            "priority": priority,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data=payload, headers=headers)
            return response.json()

    async def send_image(self, to: str, image_url: str, caption: str = "") -> dict:
        to_clean = to.replace("@c.us", "").replace("+", "").strip()
        url = f"{self.base_url}/messages/image"
        payload = {
            "token": self.token,
            "to": to_clean,
            "image": image_url,
            "caption": caption,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data=payload, headers=headers)
            return response.json()
