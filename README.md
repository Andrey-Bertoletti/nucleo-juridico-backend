# nucleo-juridico-backend

Backend (API REST) do **Sistema de Gestão de Atendimento Jurídico (NPJ-ITES)** — responsável por atendimento, clientes/assistidos, triagem, documentos, orientação de professores, agenda de retornos e relatórios.

---

## Descrição

O sistema substitui as planilhas e cadernos físicos do Núcleo de Práticas Jurídicas. Centraliza atendimentos, registra triagem, controla documentos no Supabase Storage, organiza a orientação de professores, mantém agenda de retornos e gera relatórios.

## Objetivo

Oferecer uma API segura, com escopo automático por perfil (aluno, professor, coordenação), rastreabilidade completa via histórico append-only e integração com Supabase Auth + Storage.

## Stack

- **Python 3.12**
- **FastAPI** + **Uvicorn** (ASGI)
- **SQLAlchemy 2.0** + **psycopg 3** (PostgreSQL)
- **Pydantic v2** / **pydantic-settings**
- **Supabase** (Auth + Storage + Postgres)
- **PyJWT[crypto]** (validação HS256 e ES256/RS256 via JWKS)

## Funcionalidades (MVP)

- Auth: login/logout/me/register via Supabase Auth (JWT)
- CRUD de clientes/assistidos com validação de CPF (dígitos verificadores)
- Atendimentos com 10 status, encaminhamento, histórico granular
- Triagem 1:1 por atendimento
- Upload de documentos no Supabase Storage (bucket privado, signed URLs)
- Orientações com 4 decisões que disparam transição de status
- Agenda de retornos (lista + calendário)
- Dashboard + relatórios com escopo por perfil
- Administração (usuários, áreas jurídicas, tipos de demanda)

## Perfis de acesso

| Perfil | Capacidades |
|---|---|
| `aluno_estagiario` | Cadastra cliente, abre atendimento, preenche triagem, anexa documento, encaminha ao professor; vê apenas o que é responsável |
| `professor_orientador` | Recebe casos, analisa, registra orientação com decisão; vê apenas casos sob sua orientação |
| `admin_coordenacao` | Visão completa; CRUD de usuários, áreas e tipos de demanda; remove documentos; muda status de qualquer atendimento |

## Estrutura

```
nucleo-juridico-backend/
├── app/
│   ├── main.py                  # FastAPI app, CORS, exception handlers, routers
│   ├── core/
│   │   ├── settings.py          # pydantic-settings + auto-fix DATABASE_URL
│   │   ├── security.py          # decode_supabase_jwt (HS256 e ES256/RS256)
│   │   ├── dependencies.py      # get_current_user, require_admin/teacher/student
│   │   └── exceptions.py        # handler global 500
│   ├── database/
│   │   └── session.py           # engine + SessionLocal + Base + get_db
│   ├── services/
│   │   ├── supabase_client.py   # clientes anon e admin (cacheados)
│   │   └── history.py           # helper central de auditoria
│   └── modules/                 # módulos de domínio
│       ├── auth/                # login/register/logout/me
│       ├── users/               # CRUD de usuários
│       ├── admin/               # /admin/* (usuários, áreas, tipos)
│       ├── clients/             # CRUD + histórico
│       ├── attendances/         # 10 status, send-to-teacher, histórico
│       ├── triage/              # ficha 1:1
│       ├── documents/           # upload Storage + signed URL
│       ├── orientations/        # /teacher/cases + decisões
│       ├── appointments/        # agenda (lista + calendário)
│       ├── catalogs/            # legal_areas, demand_types, teachers, students
│       └── reports/             # dashboard + 7 relatórios
├── scripts/
│   └── seed_users.py            # cria admin + professor de exemplo
├── supabase/
│   └── migrations/              # 8 migrations
├── .env.example
├── render.yaml                  # blueprint do Render
├── runtime.txt                  # Python 3.12.5
└── requirements.txt
```

## Como rodar localmente

```powershell
# 1) criar venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) instalar dependências
pip install -r requirements.txt

# 3) copiar e preencher variáveis
copy .env.example .env

# 4) aplicar migrations (via Supabase CLI)
supabase db push

# 5) (opcional) criar usuários de seed
python scripts/seed_users.py

# 6) rodar dev server
uvicorn app.main:app --reload
```

API em `http://localhost:8000`. Docs em `/docs`.

## Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `APP_ENV` | não | `development` ou `production`. Default `development`. |
| `APP_DEBUG` | não | `true` em dev exibe stack trace nos erros 500. Default `true`. |
| `DATABASE_URL` | **sim** | Connection string do Postgres (use o **Transaction Pooler** do Supabase). O prefixo `postgresql://` é convertido automaticamente para `postgresql+psycopg://`. |
| `SUPABASE_URL` | **sim** | URL do projeto Supabase. |
| `SUPABASE_ANON_KEY` | **sim** | Chave pública (anon) — usada em `sign_in_with_password` e em `sign_up`. |
| `SUPABASE_SERVICE_ROLE_KEY` | **sim** | Chave secreta — usada para criar usuários e gerar signed URLs do Storage. **Nunca exponha no frontend.** |
| `SUPABASE_JWT_SECRET` | **sim** | JWT Secret do Supabase — usado para validar tokens HS256 (legacy). |
| `SUPABASE_STORAGE_BUCKET` | não | Nome do bucket. Default `documentos`. |
| `CORS_ORIGINS` | **sim** | Lista de origens permitidas separadas por vírgula. Ex.: `https://nucleo-juridico-frontend.vercel.app`. |
| `CORS_ORIGIN_REGEX` | não | Regex para liberar previews do Vercel. Ex.: `^https://nucleo-juridico-frontend(-[\w-]+)?\.vercel\.app$`. |
| `JWT_ALGORITHM` | não | Default `HS256`. O backend detecta ES256/RS256 automaticamente via JWKS. |
| `JWT_AUDIENCE` | não | Default `authenticated` (audience dos tokens do Supabase). |

> Veja [`.env.example`](./.env.example) e o checklist em [DEPLOY.md](./DEPLOY.md).

## Scripts disponíveis

| Comando | Descrição |
|---|---|
| `uvicorn app.main:app --reload` | Dev server com hot-reload |
| `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | Start de produção |
| `python scripts/seed_users.py` | Cria os usuários `admin@ites.edu.br` e `professor@ites.edu.br` |
| `supabase db push` | Aplica as migrations no Supabase remoto |
| `supabase db reset` | Reseta o banco local e aplica migrations |

## Documentação relacionada

- [DEPLOY.md](./DEPLOY.md) — passo a passo para subir backend, frontend e Supabase
- [DATABASE.md](./DATABASE.md) — schema, migrations e tabelas
- [API.md](./API.md) — lista de endpoints com permissões
- [MVP_CHECKLIST.md](./MVP_CHECKLIST.md) — o que foi entregue
- [PRESENTATION.md](./PRESENTATION.md) — roteiro de apresentação
- [PROJECT_SCOPE.md](./PROJECT_SCOPE.md) — escopo original
