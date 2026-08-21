# Smart Assistant — Bot de Atendimento & Vendas WhatsApp

Bot profissional de atendimento focado em **vendas e retenção** para a empresa **Smart Assistant**.

## Funcionalidades

1. **Atendimento inteligente no WhatsApp** (via Ultramsg)
   - Respostas profissionais com IA (OpenAI)
   - Foco em qualificação, conversão e retenção
   - Coleta automática de dados do cliente

2. **Base de dados de clientes**
   - Nome, empresa, tipo de negócio, tamanho
   - Status do funil (lead → qualificado → proposta → cliente / perdido)
   - Pacote comprado e motivo de não compra
   - Score de potencial (0-100)
   - Histórico de conversas

3. **Painel Web (Dashboard)**
   - KPIs de vendas e conversão
   - Lista de clientes filtrável
   - Detalhe de cada lead
   - Análise de Meta Ads

4. **Análise de campanhas Meta Ads**
   - Sincronização de insights
   - Recomendações automáticas

## Pacotes da Smart Assistant

| Pacote    | Preço     | O que inclui                                              |
|-----------|-----------|-----------------------------------------------------------|
| **Básico**   | 5.000 MT | Até 100 mensagens + controle de vendas                   |
| **Business** | 8.700 MT | Mensagens ilimitadas + controle + insights de vendas     |
| **Pro**      | 12.000 MT| Tudo do Business + assistente de marketing AI            |

---

## Stack Técnica

- **Python 3.11+**
- **FastAPI** + Uvicorn
- **SQLAlchemy** (async) + SQLite / PostgreSQL
- **OpenAI** (GPT-4o-mini ou superior)
- **Ultramsg** (WhatsApp API)
- **Meta Marketing API** (opcional)
- **Render** para hospedagem
- **GitHub** para versionamento

---

## Setup Local (5 minutos)

### 1. Clone e ambiente

```bash
git clone https://github.com/SEU_USUARIO/smart-assistant-bot.git
cd smart-assistant-bot
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure o `.env`

```bash
cp .env.example .env
```

Edite o `.env` com:

```env
ULTRAMSG_INSTANCE_ID=instanceXXXX
ULTRAMSG_TOKEN=seu_token_ultramsg
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
DATABASE_URL=sqlite+aiosqlite:///./smart_assistant.db
APP_URL=http://localhost:8000
COMPANY_NAME=Smart Assistant
```

### 3. Rode o servidor

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Acesse: http://localhost:8000

### 4. Configure o Webhook no Ultramsg

1. Vá em **Instance Settings** no painel Ultramsg
2. Coloque a URL do webhook: `https://SEU-DOMINIO/webhook`
3. Ative `webhook_message_received = true`

Para testes locais use **ngrok**:

```bash
ngrok http 8000
```

Depois cole a URL do ngrok + `/webhook` nas configurações do Ultramsg.

---

## Deploy no Render

1. Faça push do projeto para o GitHub
2. No Render → **New Web Service**
3. Conecte o repositório
4. Configurações:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Adicione as variáveis de ambiente (as mesmas do `.env`)
6. Para produção, use PostgreSQL:
   - Crie um PostgreSQL no Render
   - Use a connection string em `DATABASE_URL` (troque `postgres://` por `postgresql+asyncpg://`)

Após o deploy, configure o webhook no Ultramsg com a URL do Render:

```
https://seu-app.onrender.com/webhook
```

---

## Estrutura do Projeto

```
smart-assistant-bot/
├── app/
│   ├── main.py              # Entrada FastAPI
│   ├── config.py            # Configurações
│   ├── database.py          # SQLAlchemy async
│   ├── models.py            # Tabelas
│   ├── schemas.py           # Pydantic
│   ├── bot/
│   │   ├── whatsapp.py      # Cliente Ultramsg
│   │   ├── ai.py            # Prompt + OpenAI + function calling
│   │   └── handlers.py      # Processamento de mensagens
│   ├── services/
│   │   ├── client_service.py
│   │   └── meta_ads.py
│   └── api/
│       └── routes.py        # Webhook + Dashboard + API
├── templates/               # Painel HTML (Tailwind)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Como o bot funciona

1. Cliente envia mensagem no WhatsApp
2. Ultramsg dispara o webhook → `/webhook`
3. O bot:
   - Cria/atualiza o cliente na base
   - Salva a mensagem
   - Chama a IA com histórico + dados do cliente
   - A IA pode atualizar dados via function calling
   - Responde de forma profissional e focada em vendas
4. Você acompanha tudo no painel em tempo real

---

## Próximos passos recomendados

- [ ] Adicionar autenticação simples no painel (senha)
- [ ] Integração de pagamento (M-Pesa / Emola / etc.)
- [ ] Follow-up automático (APScheduler)
- [ ] Relatórios por email semanal
- [ ] Multi-usuário / multi-empresa (SaaS)

---

Feito com ❤️ para a **Smart Assistant**
