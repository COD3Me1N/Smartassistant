from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.whatsapp import UltramsgClient
from app.bot.ai import generate_response
from app.services.client_service import (
    get_or_create_client,
    update_client,
    save_message,
    get_conversation_history,
)


ultramsg = UltramsgClient()


async def process_incoming_message(db: AsyncSession, webhook_data: dict) -> str:
    """
    Processa mensagem recebida do webhook Ultramsg.
    Formato esperado:
    {
      "event_type": "message_received",
      "instanceId": "...",
      "data": {
        "id": "...",
        "from": "2588XXXXXXX@c.us",
        "to": "...",
        "body": "texto da mensagem",
        "fromMe": false,
        "type": "chat",
        ...
      }
    }
    """
    try:
        data = webhook_data.get("data") or webhook_data
        if isinstance(data, list):
            data = data[0] if data else {}

        if data.get("fromMe"):
            return "ignored_from_me"

        phone = data.get("from") or data.get("chatId") or ""
        body = data.get("body") or data.get("text") or ""
        msg_type = data.get("type", "chat")

        if not phone or not body:
            return "no_phone_or_body"

        if msg_type != "chat":
            # Por enquanto só processamos texto
            await ultramsg.send_message(
                phone,
                "No momento consigo responder apenas mensagens de texto. Pode escrever o que precisa?",
            )
            return "non_text"

        # 1. Garante cliente na base
        client = await get_or_create_client(db, phone)

        # 2. Salva mensagem do usuário
        await save_message(db, phone, "user", body)

        # 3. Histórico
        history = await get_conversation_history(db, phone)

        # 4. Dados atuais do cliente para contexto da IA
        client_data = {
            "name": client.name,
            "company_name": client.company_name,
            "company_type": client.company_type,
            "company_size": client.company_size,
            "status": client.status,
            "package_bought": client.package_bought,
            "score": client.score,
            "conversation_summary": client.conversation_summary,
        }

        # 5. Gera resposta da IA
        reply, updated_data = await generate_response(
            phone=phone,
            user_message=body,
            history=history,
            client_data=client_data,
        )

        # 6. Atualiza dados se a IA extraiu informações
        if updated_data:
            await update_client(db, phone, updated_data)

        # 7. Salva resposta da IA
        await save_message(db, phone, "assistant", reply)

        # 8. Envia via Ultramsg
        await ultramsg.send_message(phone, reply)

        return "ok"

    except Exception as e:
        print(f"[Handler Error] {e}")
        return f"error: {str(e)}"
