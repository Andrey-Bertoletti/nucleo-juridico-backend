# nucleo-juridico-backend

Backend (API REST) do **Sistema de Gestão de Atendimento Jurídico** — responsável por expor os recursos de atendimento, clientes/assistidos, triagem, documentos, orientação de professores e acompanhamento de casos.

---

## Stack

- **Python 3.11+**
- **FastAPI** (framework web)
- **Uvicorn** (ASGI server)
- **SQLAlchemy** + **Alembic** (ORM e migrações)
- **Pydantic v2** (validação e schemas)
- **PostgreSQL** gerenciado pelo **Supabase**
- **Supabase Storage** para documentos
- Autenticação via **Supabase Auth** (validação de JWT)

---

## Estrutura de pastas

```
nucleo-juridico-backend/
├── app/
│   ├── main.py         # Entrada da aplicação FastAPI
│   ├── core/           # Configuração, settings, segurança, dependências globais
│   ├── modules/        # Módulos de domínio (rotas + lógica por feature)
│   ├── database/       # Sessão do banco, modelos ORM, migrações
│   ├── schemas/        # Schemas Pydantic (request/response)
│   ├── services/       # Regras de negócio reutilizáveis e integrações externas
│   └── utils/          # Funções utilitárias genéricas
├── .env.example
├── .gitignore
├── PROJECT_SCOPE.md
├── requirements.txt
└── README.md
```

### Convenções por pasta

| Pasta         | Responsabilidade                                                                 |
|---------------|----------------------------------------------------------------------------------|
| `main.py`     | Cria a instância FastAPI, registra middlewares e inclui os routers de `modules/`. |
| `core/`       | `settings` (env vars), `security` (JWT/Supabase), dependências de injeção comuns. |
| `modules/`    | Cada subpasta = um domínio (`atendimento`, `clientes`, `casos`...) com `router.py`, `service.py`, etc. |
| `database/`   | `session.py`, `base.py`, modelos SQLAlchemy e diretório de migrações Alembic.    |
| `schemas/`    | Schemas Pydantic globais. Schemas específicos podem viver dentro do módulo.       |
| `services/`   | Lógica de negócio compartilhada entre módulos e integrações (Supabase Storage, e-mail, etc.). |
| `utils/`      | Helpers puros (formatadores, parsers, validações genéricas).                      |

---

## Como rodar (após o setup do projeto)

```bash
# 1) criar e ativar venv (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) instalar dependências
pip install -r requirements.txt

# 3) copiar variáveis de ambiente
copy .env.example .env
# edite o .env com as credenciais reais

# 4) rodar em modo desenvolvimento
uvicorn app.main:app --reload
```

A API ficará disponível em `http://localhost:8000`. A documentação interativa em `http://localhost:8000/docs`.

---

## Deploy no Render

O projeto já vem com [`render.yaml`](./render.yaml) e [`runtime.txt`](./runtime.txt) preparados — basta seguir os passos abaixo.

### Pré-requisitos

1. Repositório no GitHub (✅ já configurado: `Andrey-Bertoletti/nucleo-juridico-backend`).
2. Migrações aplicadas no Supabase (`supabase db push`).
3. Coleta das credenciais que ficarão como variáveis de ambiente.

### Variáveis de ambiente que você vai precisar

| Variável | Onde encontrar |
|---|---|
| `DATABASE_URL` | Supabase → Project Settings → **Database** → "Connection string" → **Transaction pooler** (porta 6543). Prefixar com `postgresql+psycopg://` e trocar `[YOUR-PASSWORD]` pela senha do banco. |
| `SUPABASE_URL` | Supabase → Project Settings → API → "Project URL". |
| `SUPABASE_ANON_KEY` | Supabase → Project Settings → API → "anon public". |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API → "service_role" (segredo!). |
| `SUPABASE_JWT_SECRET` | Supabase → Project Settings → API → "JWT Secret". |
| `CORS_ORIGINS` | URL(s) do frontend, separadas por vírgula. Ex.: `https://nucleo-juridico-frontend.vercel.app`. |

> Use a Transaction pooler (porta 6543) e **não** a conexão direta (porta 5432) — o free do Render dorme e reabre conexões com frequência.

### Passo a passo via dashboard (recomendado)

1. Acesse [dashboard.render.com](https://dashboard.render.com) e clique em **New + → Blueprint**.
2. Conecte sua conta do GitHub e selecione o repositório `nucleo-juridico-backend`.
3. O Render detecta o `render.yaml` e mostra o serviço `nucleo-juridico-backend`. Clique **Apply**.
4. Preencha cada variável marcada como **"Set value"** (todas as `sync: false` do blueprint). As que têm `value:` no YAML já vêm preenchidas.
5. Clique **Create Resources**. O primeiro build leva ~3-5 min.
6. Quando finalizar, copie a URL final (ex.: `https://nucleo-juridico-backend.onrender.com`) — você vai precisar para configurar o frontend.

### Passo a passo manual (sem blueprint)

Se preferir não usar o `render.yaml`:

1. **New + → Web Service** → conectar o repositório.
2. Configurar:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips=*`
   - **Health Check Path**: `/health`
3. Em **Environment**, adicionar todas as variáveis listadas acima + `APP_ENV=production`, `APP_DEBUG=false`, `JWT_ALGORITHM=HS256`, `JWT_AUDIENCE=authenticated`.
4. **Create Web Service**.

### Após o deploy

1. **Testar a saúde**: abrir `https://SEU-SERVICO.onrender.com/health` — deve retornar `{"status":"ok"}`.
2. **Testar a documentação**: abrir `/docs` — Swagger UI com todas as rotas.
3. **Conectar o frontend**: no projeto da Vercel, definir `NEXT_PUBLIC_API_BASE_URL=https://SEU-SERVICO.onrender.com` e redeployar o frontend.
4. **Voltar no CORS**: ajustar `CORS_ORIGINS` no Render para incluir o domínio final do frontend.
5. **Criar usuários iniciais**: rodar localmente `python scripts/seed_users.py` apontando o `.env` para os dados de produção (ou criar manualmente pelo Supabase Studio).

### Observações sobre o plano free

- O serviço **dorme após ~15 min sem tráfego**. A primeira request acorda o servidor (cold start de ~30 s).
- Sem disco persistente — não armazene arquivos no FS do Render. Documentos vão para o Supabase Storage.
- Para produção sem cold start, faça upgrade para o plano **Starter** ($7/mês).

---

## Documentação relacionada

- [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) — escopo, perfis de usuário e funcionalidades planejadas.
- Repositório do frontend: `nucleo-juridico-frontend`.
