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

### 1.4.1. SMTP custom (OBRIGATÓRIO para reset de senha funcionar)

> O Supabase usa um SMTP interno de teste que entrega **apenas** para e-mails de membros do projeto e tem rate-limit de ~4 e-mails/hora. Sem SMTP custom, **o reset de senha não chega para usuários finais** — esse é o motivo #1 de "mandei o link e ele nunca recebeu".

Em **Project Settings → Authentication → SMTP Settings → Enable Custom SMTP**:

| Campo | Valor de exemplo (Resend) |
|---|---|
| **Sender email** | `no-reply@seu-dominio.com.br` |
| **Sender name** | `Núcleo de Práticas Jurídicas — ITES` |
| **Host** | `smtp.resend.com` |
| **Port** | `587` (STARTTLS) ou `465` (SSL) |
| **Username** | `resend` |
| **Password** | API key do Resend (`re_xxx…`) |

> Provedores recomendados (free tier suficiente para o volume do NPJ): **Resend**, **SendGrid**, **Brevo**, **Postmark**. Gmail/Outlook **não** funcionam — eles bloqueiam SMTP autenticado de serviços não-Google/MS.

Em **Authentication → Rate Limits**:
- **Emails sent**: subir de 4/hora para ao menos 30/hora (depois do SMTP custom o limite default cai para o do provedor).

### 1.4.2. URLs de redirecionamento

Em **Authentication → URL Configuration**:

- **Site URL**: `https://nucleo-juridico-frontend-fon2.vercel.app`
- **Redirect URLs** (adicionar TODAS as variações abaixo, uma por linha):
  - `https://nucleo-juridico-frontend-fon2.vercel.app`
  - `https://nucleo-juridico-frontend-fon2.vercel.app/login` (callback do Google OAuth)
  - `https://nucleo-juridico-frontend-fon2.vercel.app/reset-password` (convite + reset)
  - `https://nucleo-juridico-frontend-fon2.vercel.app/**` (libera previews da Vercel)
  - `http://localhost:3000/login` (desenvolvimento — Google OAuth)
  - `http://localhost:3000/reset-password` (desenvolvimento — convite/reset)

> **Se a Redirect URL não estiver na allowlist, o Supabase ignora o `redirect_to` e manda o usuário para a Site URL** — o link do e-mail abre a home em vez do formulário. Sintoma clássico de allowlist faltando.

### 1.4.4. Google OAuth (login com Google)

Em **Authentication → Providers → Google**:

1. **Enable Sign in with Google**: ON.
2. **Client IDs** / **Client Secret**: vêm do **Google Cloud Console**:
   - https://console.cloud.google.com/apis/credentials → **Create Credentials** → **OAuth Client ID** → **Web application**.
   - **Authorized JavaScript origins**:
     - `https://nucleo-juridico-frontend-fon2.vercel.app`
     - `http://localhost:3000`
   - **Authorized redirect URIs** (este é o callback do Supabase, NÃO do frontend):
     - `https://kyhspzjpvughewfwbiym.supabase.co/auth/v1/callback`
   - Copie o **Client ID** e **Client Secret** gerados.
3. Cole no Dashboard do Supabase e salve.
4. (Opcional) **Skip nonce check**: ative em desenvolvimento se aparecer "nonce check failed" no localhost.

Em **OAuth consent screen** (Google Cloud):
- **User Type**: External (ou Internal se a organização do ITES tiver Workspace).
- **App name**: `NPJ-ITES — Núcleo de Práticas Jurídicas`.
- **Authorized domains**: `vercel.app` e (se aplicável) o domínio do ITES.
- Scopes mínimos: `email`, `profile`, `openid`.

> **Importante para a regra "cadastro só pelo admin"**: o frontend chama `/auth/me` depois do callback do Google. Se o usuário não tem um `profile` cadastrado, recebe 404 e a UI mostra "Sua conta do Google não está vinculada ao sistema". Para que o vínculo aconteça, o admin precisa convidar o usuário PRIMEIRO (com o mesmo e-mail Google) — o Supabase faz identity linking automaticamente quando os e-mails batem.

### 1.4.3. Templates de e-mail (Reset password e Confirm signup)

Em **Authentication → Email Templates**:

- **Reset Password** — verifique que o link aponta para `{{ .ConfirmationURL }}` (não para `{{ .SiteURL }}` puro). O backend já passa `redirect_to=…/reset-password`, então o `ConfirmationURL` resolve para a página certa.
- **Confirm signup** — só relevante se um dia habilitar self-signup; hoje o cadastro é só pelo admin.

Sugestão de assunto/conteúdo PT-BR para **Reset Password**:

```
Assunto: Redefinição de senha — NPJ-ITES

Olá,

Recebemos uma solicitação para redefinir a senha da sua conta no
Núcleo de Práticas Jurídicas (ITES).

Para continuar, clique no link abaixo (válido por 1 hora):

{{ .ConfirmationURL }}

Se você não solicitou esta redefinição, ignore este e-mail.

— Núcleo de Práticas Jurídicas / ITES
```

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
   | `FRONTEND_URL` | `https://nucleo-juridico-frontend-fon2.vercel.app` (usado nos links de convite/reset por e-mail) |
   | `CORS_ORIGINS` | `https://nucleo-juridico-frontend-fon2.vercel.app` |
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
