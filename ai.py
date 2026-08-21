import json
import re
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

client = AsyncOpenAI(
    api_key=settings.openai_api_key or "no-key",
    base_url=settings.openai_base_url,
)

SYSTEM_PROMPT = f"""Tu és o consultor comercial da {settings.company_name}, empresa em Moçambique que cria bots de WhatsApp para empresas.

PERSONALIDADE:
- Humano, simpático e confiante — como um bom vendedor no WhatsApp, não um robô
- Falas português de Moçambique, natural e simples
- Nunca repetis a mesma frase nem a mesma pergunta
- Adaptas-te ao que o cliente acabou de dizer

O QUE FAZES:
1. Cumprimentas de forma natural (só na primeira mensagem)
2. Descobres o negócio e a maior dor (atendimento, leads perdidos, vendas, etc.)
3. Mostras como um bot resolve ISSO concretamente
4. Só depois apresentas o pacote certo
5. Guías para o próximo passo sem pressionar de mais

PACOTES (só quando fizer sentido falar de preço):
• Básico — 5.000 MT → até 100 msgs + controlo de vendas
• Business — 8.700 MT → msgs ilimitadas + controlo + insights de vendas
• Pro — 12.000 MT → tudo do Business + assistente de marketing AI

REGRAS DE OURO:
- UMA pergunta por mensagem
- Respostas curtas (2 a 4 frases no máximo)
- NUNCA copies mensagens anteriores tuas
- NUNCA faças spam de preço ou lista de pacotes logo de início
- Se o cliente disser só "Oi" / "Olá" → cumprimenta e pergunta o que faz a empresa dele
- Se o cliente já explicou a dor → conecta a solução e avança
- Se pedir preço → recomenda 1 pacote (o mais adequado) e explica porque
- Se hesitar → mostra valor, não repetas o mesmo argumento
- Se disser que não quer → pergunta o motivo uma vez; se insistir, fecha educadamente

EXEMPLOS DE TOM BOM:
Cliente: "Oi"
Tu: "Olá! Tudo bem? Sou da Smart Assistant. Qual é o tipo de negócio da sua empresa?"

Cliente: "Tenho uma loja online"
Tu: "Boa. E como está a ser o atendimento no WhatsApp — conseguem responder a todos os clientes a tempo?"

Cliente: "Perdemos muitos leads"
Tu: "Isso é comum. Um bot responde na hora, 24/7, e já qualifica o cliente para a sua equipa. Quer que eu lhe mostre como funciona na prática?"

Nunca inventes funcionalidades. Nunca digas que és uma IA. Fala sempre como pessoa da equipa Smart Assistant.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_client_data",
            "description": "Atualiza dados do cliente quando descobrires informações novas",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "company_name": {"type": "string"},
                    "company_type": {"type": "string"},
                    "company_size": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["lead", "qualified", "proposta", "cliente", "perdido"],
                    },
                    "package_bought": {
                        "type": "string",
                        "enum": ["none", "basico", "business", "pro"],
                    },
                    "reason_not_bought": {"type": "string"},
                    "score": {"type": "integer"},
                    "conversation_summary": {"type": "string"},
                    "notes": {"type": "string"},
                },
            },
        },
    }
]


def _extract_json_from_text(text: str) -> dict | None:
    if not text:
        return None
    match = re.search(r"\{[^{}]*\"(?:name|company_name|status|score)\"[^{}]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


async def generate_response(
    phone: str,
    user_message: str,
    history: list[dict],
    client_data: dict | None = None,
    pushname: str | None = None,
) -> tuple[str, dict | None]:
    if not settings.openai_api_key:
        return (
            "Olá! Sou da Smart Assistant. Em que tipo de negócio trabalha?",
            None,
        )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if client_data or pushname:
        nome = (client_data or {}).get("name") or pushname or "Desconhecido"
        context = (
            f"CONTEXTO DO CONTACTO:\n"
            f"- Telefone: {phone}\n"
            f"- Nome WhatsApp: {nome}\n"
            f"- Empresa: {(client_data or {}).get('company_name') or 'ainda não sei'}\n"
            f"- Tipo: {(client_data or {}).get('company_type') or 'ainda não sei'}\n"
            f"- Status: {(client_data or {}).get('status') or 'lead'}\n"
            f"- Pacote: {(client_data or {}).get('package_bought') or 'none'}\n"
            f"- Resumo: {(client_data or {}).get('conversation_summary') or 'primeira conversa'}\n\n"
            f"Usa o nome se souberes. NÃO repitas o que já perguntaste no histórico."
        )
        messages.append({"role": "system", "content": context})

    # Histórico sem duplicar a mensagem atual
    for msg in history[-10:]:
        role = msg.get("role") or "user"
        content = (msg.get("content") or "").strip()
        if content and role in ("user", "assistant"):
            messages.append({"role": role, "content": content})

    # Evita duplicar se a última do histórico já for esta mensagem
    if not history or history[-1].get("content") != user_message:
        messages.append({"role": "user", "content": user_message})

    # Tentativa com tools
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.85,
            max_tokens=280,
        )
        message = response.choices[0].message
        reply_text = (message.content or "").strip()
        updated_data = None

        if message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.function.name == "update_client_data":
                    try:
                        updated_data = json.loads(tool_call.function.arguments)
                    except (json.JSONDecodeError, TypeError):
                        updated_data = None
            if not reply_text:
                reply_text = "Percebi. E qual é a maior dificuldade no atendimento ou nas vendas neste momento?"

        if not updated_data:
            updated_data = _extract_json_from_text(reply_text)

        if reply_text:
            return reply_text, updated_data
    except Exception as e:
        print(f"[AI tools error] {e} — tentando sem tools...")

    # Fallback sem tools
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0.85,
            max_tokens=280,
        )
        reply_text = (response.choices[0].message.content or "").strip()
        updated_data = _extract_json_from_text(reply_text)
        if reply_text:
            return reply_text, updated_data
    except Exception as e:
        print(f"[AI Error] {e}")

    return (
        "Olá! Sou da Smart Assistant. Qual é o tipo de negócio da sua empresa?",
        None,
    )
