import json
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

client = AsyncOpenAI(api_key=settings.openai_api_key)

PACKAGES = {
    "basico": {
        "nome": "Básico",
        "preco": "5.000 MT",
        "descricao": "Receber e responder até 100 mensagens + controle de vendas",
    },
    "business": {
        "nome": "Business",
        "preco": "8.700 MT",
        "descricao": "Mensagens ilimitadas + controle de vendas + insights para melhorar as vendas",
    },
    "pro": {
        "nome": "Pro",
        "preco": "12.000 MT",
        "descricao": "Mensagens ilimitadas + controle de vendas + insights de melhoria + assistente de marketing AI",
    },
}

SYSTEM_PROMPT = f"""Você é o CLOSER de vendas da {settings.company_name} — especialista em bots de automação WhatsApp para empresas em Moçambique.

MISSÃO ÚNICA: FECHAR VENDAS. Cada conversa deve avançar para o fechamento o mais rápido possível.

PACOTES (use estes valores exatos):
• Básico — 5.000 MT → até 100 mensagens + controle de vendas
• Business — 8.700 MT → mensagens ilimitadas + controle + insights de vendas
• Pro — 12.000 MT → tudo do Business + assistente de marketing AI

ESTILO DE VENDAS (AGRESSIVO MAS PROFISSIONAL):
- Tom: direto, confiante, urgente, sem enrolação. Você é o especialista, o cliente precisa da solução.
- Faça UMA pergunta de cada vez, mas sempre com intenção de avançar.
- Use o nome do cliente sempre que souber.
- Crie urgência: "quantos clientes você está a perder hoje por não responder a tempo?", "cada dia sem bot é dinheiro que fica na mesa".
- Destaque a dor antes de apresentar o preço.
- Quando apresentar o pacote, vá direto ao ponto e peça a decisão: "Quer que eu ative o Business agora ou prefere começar pelo Básico?"
- Trate objeções de preço com valor: mostre quanto tempo/dinheiro o cliente recupera.
- Se o cliente hesitar, use scarcity e social proof de forma natural ("várias empresas do seu segmento já estão a usar e a recuperar o investimento em menos de 2 semanas").
- Nunca aceite um "vou pensar" sem tentar um próximo passo concreto (escolher pacote, confirmar dados, agendar ativação).
- Se disser que não quer, pergunte o motivo REAL e tente reverter uma vez. Se insistir, registre o motivo e mantenha a porta aberta de forma curta.

FLUXO RÁPIDO:
1. Cumprimente + descubra o negócio e a maior dor em 1-2 mensagens
2. Conecte a dor à solução (bot que responde 24/7, não perde lead, controla vendas)
3. Recomende o pacote certo e peça o fechamento
4. Confirme e oriente o próximo passo (ativação)

COLETE SEMPRE (e atualize via ferramenta):
nome, empresa, tipo de negócio, tamanho, dor principal, status do funil, pacote de interesse, score, motivo de perda.

Atualize o status: lead → qualified → proposta → cliente / perdido.

Responda em português claro (Moçambique). Seja humano, nunca robótico. Nunca invente preços ou funcionalidades.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_client_data",
            "description": "Atualiza os dados do cliente na base de dados sempre que descobrir informações novas",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nome do contato"},
                    "company_name": {"type": "string", "description": "Nome da empresa"},
                    "company_type": {
                        "type": "string",
                        "description": "Tipo de negócio (saúde, e-commerce, serviços, educação, imobiliária, etc.)",
                    },
                    "company_size": {
                        "type": "string",
                        "description": "Tamanho aproximado (1-5, 6-20, 21-50, 50+)",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["lead", "qualified", "proposta", "cliente", "perdido"],
                        "description": "Status atual do funil",
                    },
                    "package_bought": {
                        "type": "string",
                        "enum": ["none", "basico", "business", "pro"],
                        "description": "Pacote comprado ou de interesse forte",
                    },
                    "reason_not_bought": {
                        "type": "string",
                        "description": "Motivo pelo qual não comprou (se status = perdido)",
                    },
                    "score": {
                        "type": "integer",
                        "description": "Score de potencial de compra 0-100",
                    },
                    "conversation_summary": {
                        "type": "string",
                        "description": "Resumo curto da conversa atual (2-3 frases)",
                    },
                    "notes": {"type": "string", "description": "Observações importantes"},
                },
            },
        },
    }
]


async def generate_response(
    phone: str,
    user_message: str,
    history: list[dict],
    client_data: dict | None = None,
) -> tuple[str, dict | None]:
    """
    Gera resposta da IA + possíveis dados atualizados do cliente.
    Retorna: (resposta_texto, dados_para_atualizar ou None)
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if client_data:
        context = f"""
DADOS ATUAIS DO CLIENTE:
- Telefone: {phone}
- Nome: {client_data.get('name') or 'Desconhecido'}
- Empresa: {client_data.get('company_name') or 'Desconhecida'}
- Tipo: {client_data.get('company_type') or 'Desconhecido'}
- Tamanho: {client_data.get('company_size') or 'Desconhecido'}
- Status: {client_data.get('status')}
- Pacote: {client_data.get('package_bought')}
- Score: {client_data.get('score')}
- Resumo anterior: {client_data.get('conversation_summary') or 'Nenhum'}
"""
        messages.append({"role": "system", "content": context})

    # Histórico (últimas 10 mensagens)
    for msg in history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=600,
        )

        message = response.choices[0].message
        reply_text = message.content or ""
        updated_data = None

        if message.tool_calls:
            for tool_call in message.tool_calls:
                if tool_call.function.name == "update_client_data":
                    try:
                        updated_data = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        updated_data = None

            # Se a IA só chamou ferramenta sem texto, gera uma resposta curta
            if not reply_text and updated_data:
                reply_text = "Perfeito, anotei essas informações. Como posso te ajudar melhor agora?"

        return reply_text.strip(), updated_data

    except Exception as e:
        print(f"[AI Error] {e}")
        return (
            "Desculpe, estou com uma pequena instabilidade no momento. Pode repetir a sua mensagem em instantes?",
            None,
        )
