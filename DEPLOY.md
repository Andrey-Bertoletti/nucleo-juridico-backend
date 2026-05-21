# DEPLOY.md — Sistema de Gestão de Atendimento Jurídico

Passo a passo para subir o sistema em produção. A stack-alvo é:

- **Frontend** → **Vercel** (próprio do Next.js)
- **Backend** → **Render** (com blueprint `render.yaml`)
- **Banco + Auth + Storage** → **Supabase**

> Os passos também funcionam em Railway, Fly.io e VPS — basta usar os mesmos comandos e variáveis de ambiente.

---

## 0. Pré-requisitos

- Conta no [GitHub](https://github.com/) com os dois repositórios (`nucleo-juridico-backend` e `nucleo-juridico-frontend`).
- Conta no [Supabase](https://supabase.com/).
- Conta no [Render](https://render.com/) e no [Vercel](https://vercel.com/).
- (Local) Node 18+, Python 3.12, [Supabase CLI](https://supabase.com/docs/guides/cli).

---

## 1. Supabase — banco, auth e storage

### 1.1. Criar projeto

1. https://app.supabase.com → **New project** → escolha região mais próxima.
2. Anote a **Database password** — você vai precisar para a `DATABASE_URL`.

### 1.2. Aplicar migrations

Na raiz do **backend**:

```bash
supabase login
supabase link --project-ref <SEU_PROJECT_REF>
supabase db push
```

Isto aplica as 8 migrations em `supabase/migrations/`:

| # | Arquivo | Conteúdo |
|---|---|---|
| 1 | `..._initial_schema.sql` | 10 tabelas + trigger updated_at |
| 2 | `..._seed_legal_areas.sql` | 10 áreas do direito |
| 3 | `..._seed_demand_types.sql` | 46 tipos de demanda |
| 4 | `..._add_client_status_and_history.sql` | Soft-delete + `client_history` |
| 5 | `..._attendance_status_update.sql` | Novos status + coluna `notes` |
| 6 | `..._documents_taxonomy_update.sql` | Tipos/status de documentos atualizados |
| 7 | `..._orientations_decisions_update.sql` | 4 decisões do professor |
| 8 | `..._appointments_status_update.sql` | `realizado` → `compareceu` |

> Em alternativa: cole cada arquivo `.sql` no **SQL Editor** do Supabase Studio (na ordem).

### 1.3. Storage — bucket privado

1. **Storage** → **New bucket** → nome `documentos`.
2. **Public bucket**: **OFF** (privado).
3. **Allowed MIME types** (opcional): `application/pdf, image/jpeg, image/png, image/webp, application/msword, application/vnd.openxmlformats-officedocument.wordprocessingml.document`.
4. **File size limit** (opcional): 10 MB.

Como o bucket é privado, todo acesso a arquivo passa pelo backend, que gera **signed URLs** com TTL de 1 hora usando a service-role key. **Não é necessário** criar policies de Storage adicionais — a service-role bypassa RLS.

### 1.4. Auth — confirmação de e-mail

Em **Authentication → Providers → Email**:
- Para desenvolvimento, desabilite **Confirm email** (mais rápido testar).
- Para produção, mantenha habilitado e configure o template de e-mail.

### 1.5. Coletar credenciais

Em **Project Settings → API**:
- `Project URL` → `SUPABASE_URL`
- `anon public` → `SUPABASE_ANON_KEY`
- `service_role` → `SUPABASE_SERVICE_ROLE_KEY` (segredo absoluto)
- `JWT Secret` (em **JWT Settings**) → `SUPABASE_JWT_SECRET`

Em **Project Settings → Database → Connection string** copie o **Transaction pooler** (porta 6543) → `DATABASE_URL`.

> O backend converte automaticamente `postgresql://` para `postgresql+psycopg://` (driver psycopg3).

---

## 2. Backend — deploy no Render

O repositório vem com `render.yaml` configurado.

### 2.1. Via blueprint (recomendado)

1. https://dashboard.render.com → **New + → Blueprint**.
2. Conecte o repositório `nucleo-juridico-backend` no GitHub.
3. Render detecta o `render.yaml` e cria o **Web Service** automaticamente.
4. Preencha as variáveis **`sync: false`** (todas as marcadas no YAML):

   | Variável | Valor |
   |---|---|
   | `DATABASE_URL` | string do Transaction pooler (porta 6543) |
   | `SUPABASE_URL` | URL do projeto |
   | `SUPABASE_ANON_KEY` | anon key |
   | `SUPABASE_SERVICE_ROLE_KEY` | service role key |
   | `SUPABASE_JWT_SECRET` | JWT secret |
   | `CORS_ORIGINS` | URL final do frontend Vercel (ex.: `https://nucleo-juridico-frontend.vercel.app`) |
   | `CORS_ORIGIN_REGEX` | (opcional) `^https://nucleo-juridico-frontend(-[\w-]+)?\.vercel\.app$` para previews |

5. **Create Resources** → build leva ~3-5 min.

### 2.2. Comando de start

Já está definido no `render.yaml`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips=*
```

### 2.3. Healthcheck e validação

- `https://SEU-SERVICO.onrender.com/health` → `{"status":"ok"}`
- `https://SEU-SERVICO.onrender.com/docs` → Swagger UI

### 2.4. Cuidados do plano free

- **Cold start**: o serviço dorme após ~15 min sem tráfego (primeira request leva ~30s).
- **Use o Transaction Pooler do Supabase (porta 6543)**: a conexão direta (5432) usa IPv6, que o Render free não suporta.
- **Sem disco persistente**: documentos vão para o Supabase Storage.

---

## 3. Frontend — deploy na Vercel

### 3.1. Importar projeto

1. https://vercel.com/new → importe `nucleo-juridico-frontend` do GitHub.
2. Vercel detecta Next.js automaticamente.
3. **Framework Preset**: Next.js (auto).
4. **Build Command**: `npm run build` (default).
5. **Output Directory**: `.next` (default).

### 3.2. Variáveis de ambiente

Em **Settings → Environment Variables**, defina:

| Variável | Valor |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://nucleo-juridico-backend.onrender.com` |
| `NEXT_PUBLIC_SUPABASE_URL` | (opcional) URL do Supabase — reservado para evolução |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | (opcional) anon key — reservado |
| `NEXT_PUBLIC_APP_ENV` | `production` |

> Habilite as variáveis para **Production**, **Preview** e **Development**.

### 3.3. Garantir o domínio no CORS

Depois do primeiro deploy, copie a URL final da Vercel (ex.: `https://nucleo-juridico-frontend.vercel.app`) e atualize a env `CORS_ORIGINS` no Render. Faça o **Manual Deploy** do backend para aplicar.

### 3.4. Promover preview a produção

A primeira branch (`main`) já vira produção. Para subir mudanças:

```bash
git push origin main
```

A Vercel constrói e publica automaticamente.

---

## 4. Criar usuários iniciais

Com backend rodando e migrations aplicadas:

```bash
# localmente, com .env apontando para o Supabase de produção
python scripts/seed_users.py
```

Cria:
- `admin@ites.edu.br` / `Admin@1234` — admin_coordenacao
- `professor@ites.edu.br` / `Professor@1234` — professor_orientador

**Troque essas senhas antes de qualquer uso real.**

---

## 5. Checklist final

### Antes do go-live

- [ ] Migrations aplicadas no Supabase
- [ ] Bucket `documentos` criado como **privado**
- [ ] Variáveis do Render preenchidas + service redeploya verde
- [ ] `/health` retorna 200
- [ ] `/docs` abre o Swagger
- [ ] Variáveis da Vercel preenchidas com a URL do Render
- [ ] `CORS_ORIGINS` no Render contém a URL final da Vercel
- [ ] Senhas dos usuários seed trocadas

### Smoke test pós-deploy

- [ ] Login no frontend com o usuário admin
- [ ] Criar um cliente novo (testa validação de CPF)
- [ ] Abrir atendimento, preencher triagem
- [ ] Anexar um PDF (testa Supabase Storage)
- [ ] Encaminhar ao professor → logar como professor → registrar orientação com decisão
- [ ] Agendar um retorno e ver no Calendário
- [ ] Abrir Relatórios → filtrar por período
- [ ] Logout e tentar acessar `/dashboard` (deve redirecionar para `/login`)

### Segurança

- [ ] `.env` real **nunca** commitado (verificar `.gitignore`)
- [ ] `SUPABASE_SERVICE_ROLE_KEY` só no backend
- [ ] Bucket privado confirmado
- [ ] `APP_DEBUG=false` em produção
- [ ] Storage bucket sem policy pública

---

## 6. Alternativas de deploy

### Railway

- Mesmo Dockerfile/buildpack Python.
- Variáveis idênticas.
- Sem cold start (plano $5/mês).

### Fly.io

- Use `fly launch` na raiz do backend; ajuste `fly.toml` para usar a internal port 8000.

### VPS (Hetzner / DigitalOcean / OCI free)

1. Instale Python 3.12 e Postgres.
2. Clone o repo, crie venv, instale requirements.
3. Configure systemd para `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
4. Use **Caddy** ou **nginx** como reverse proxy com TLS automático.
5. Variáveis em `/etc/nucleo-juridico.env`, carregadas pelo systemd.

### Vercel (frontend) com outro backend

Independentemente de onde o backend rodar, basta apontar `NEXT_PUBLIC_API_BASE_URL` para a URL pública correta e atualizar `CORS_ORIGINS` no backend.
