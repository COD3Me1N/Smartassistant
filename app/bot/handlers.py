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
    try:
        data = webhook_data.get("data") or webhook_data
        if isinstance(data, list):
            data = data[0] if data else {}

        if data.get("fromMe") or data.get("self"):
            return "ignored_from_me"

        phone = data.get("from") or data.get("chatId") or ""
        body = (data.get("body") or data.get("text") or "").strip()
        msg_type = data.get("type", "chat")
        pushname = (data.get("pushname") or "").strip() or None

        if not phone or not body:
            return "no_phone_or_body"

        if msg_type != "chat":
            await ultramsg.send_message(
                phone,
                "Por agora respondo só a mensagens de texto. Pode escrever o que precisa?",
            )
            return "non_text"

        # 1. Cliente
        client = await get_or_create_client(db, phone)

        # Guarda o nome do WhatsApp se ainda não tivermos nome
        if pushname and not client.name:
            await update_client(db, phone, {"name": pushname})
            client.name = pushname

        # 2. Histórico ANTES de gravar a mensagem atual (evita duplicar no contexto)
        history = await get_conversation_history(db, phone)

        # 3. Grava mensagem do utilizador
        await save_message(db, phone, "user", body)

        client_data = {
            "name": client.name or pushname,
            "company_name": client.company_name,
            "company_type": client.company_type,
            "company_size": client.company_size,
            "status": client.status,
            "package_bought": client.package_bought,
            "score": client.score,
            "conversation_summary": client.conversation_summary,
        }

        # 4. IA
        reply, updated_data = await generate_response(
            phone=phone,
            user_message=body,
            history=history,
            client_data=client_data,
            pushname=pushname,
        )

        if not reply or not reply.strip():
            reply = "Olá! Em que posso ajudar a sua empresa hoje?"

        # 5. Atualiza dados extraídos
        if updated_data:
            await update_client(db, phone, updated_data)

        # 6. Grava e envia resposta
        await save_message(db, phone, "assistant", reply)
        result = await ultramsg.send_message(phone, reply)
        print(f"[Send] to={phone} result={result}")

        return "ok"

    except Exception as e:
        print(f"[Handler Error] {e}")
        return f"error: {str(e)}"
