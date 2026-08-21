import json
import re
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

client = AsyncOpenAI(
    api_key=settings.openai_api_key or "no-key",
    base_url=settings.openai_base_url,
)

SYSTEM_PROMPT = f"""Tu és o consultor comercial da {settings.company_name}, em Moçambique. Criam bots de WhatsApp para empresas.

PERSONALIDADE:
- Humano, simpático e natural no WhatsApp
- Português de Moçambique, simples e claro
- Nunca repetis a mesma frase
- Nunca soas a robô nem a script

COMO CONVERSAS:
1. Se for "Oi/Olá" → cumprimenta e pergunta o tipo de negócio
2. Quando souberes o negócio → pergunta a maior dificuldade (atendimento, leads, vendas)
3. Quando souberes a dor → explica como o bot resolve ISSO
4. Só depois fala de pacote e preço
5. Guías para o próximo passo sem pressão excessiva

PACOTES (só quando o cliente pedir preço ou estiver pronto):
• Básico — 5.000 MT → até 100 msgs + controlo de vendas
• Business — 8.700 MT → msgs ilimitadas + controlo + insights
• Pro — 12.000 MT → tudo + assistente de marketing AI

REGRAS:
- SEMPRE responde com texto ao cliente (nunca fiques só a "anotar")
- UMA pergunta por mensagem
- 2 a 4 frases no máximo
- Não faças spam de preços no início
- Não digas "Perfeito, anotei" — responde de forma natural ao que a pessoa disse
- Não digas que és uma IA

Exemplo:
Cliente: Oi
Tu: Olá! Tudo bem? Sou da Smart Assistant. Qual é o tipo de negócio da sua empresa?

Cliente: Tenho uma loja
Tu: Boa. E como está a correr o atendimento no WhatsApp — conseguem responder a todos a tempo?
"""


async def generate_response(
    phone: str,
    user_message: str,
    history: list[dict],
    client_data: dict | None = None,
    pushname: str | None = None,
) -> tuple[str, dict | None]:
    if not settings.openai_api_key:
        return ("Olá! Sou da Smart Assistant. Em que tipo de negócio trabalha?", None)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    nome = (client_data or {}).get("name") or pushname or None
    if client_data or pushname:
        context = (
            f"Contacto: {phone}\n"
            f"Nome: {nome or 'desconhecido'}\n"
            f"Empresa: {(client_data or {}).get('company_name') or 'ainda não sei'}\n"
            f"Tipo: {(client_data or {}).get('company_type') or 'ainda não sei'}\n"
            f"Status: {(client_data or {}).get('status') or 'lead'}\n"
            f"Resumo: {(client_data or {}).get('conversation_summary') or 'início da conversa'}\n"
            f"Responde SEMPRE com uma mensagem natural ao cliente. Não digas só que anotaste."
        )
        messages.append({"role": "system", "content": context})

    for msg in history[-10:]:
        role = msg.get("role") or "user"
        content = (msg.get("content") or "").strip()
        if content and role in ("user", "assistant"):
            messages.append({"role": role, "content": content})

    if not history or history[-1].get("content") != user_message:
        messages.append({"role": "user", "content": user_message})

    updated_data = None

    # Chamada principal SEM tools → resposta sempre natural
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0.9,
            max_tokens=300,
        )
        reply_text = (response.choices[0].message.content or "").strip()
        if reply_text and len(reply_text) > 5:
            # Extrai dados em chamada separada (não bloqueia a resposta)
            try:
                extract_msgs = messages + [
                    {"role": "assistant", "content": reply_text},
                    {
                        "role": "user",
                        "content": (
                            "Com base nesta conversa, se houver dados novos do cliente "
                            "(nome, empresa, tipo, status, score), devolve APENAS um JSON "
                            "válido. Se não houver nada novo, devolve {}"
                        ),
                    },
                ]
                extract = await client.chat.completions.create(
                    model=settings.openai_model,
                    messages=extract_msgs,
                    temperature=0.1,
                    max_tokens=150,
                )
                raw = (extract.choices[0].message.content or "").strip()
                match = re.search(r"\{[\s\S]*\}", raw)
                if match:
                    data = json.loads(match.group())
                    if isinstance(data, dict) and data:
                        updated_data = data
            except Exception as e:
                print(f"[Extract skip] {e}")

            return reply_text, updated_data
    except Exception as e:
        print(f"[AI Error] {e}")

    low = user_message.lower().strip()
    if low in ("oi", "olá", "ola", "hey", "bom dia", "boa tarde", "boa noite"):
        return (
            f"Olá{(' ' + nome) if nome else ''}! Tudo bem? Sou da Smart Assistant. "
            "Qual é o tipo de negócio da sua empresa?",
            updated_data,
        )

    return (
        "Obrigado pela mensagem. Pode contar-me um pouco sobre o seu negócio "
        "e o que gostaria de melhorar no atendimento ou nas vendas?",
        updated_data,
    )
