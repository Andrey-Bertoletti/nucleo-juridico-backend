# API.md — Endpoints e Permissões

> A documentação interativa fica em `/docs` (Swagger UI) e `/redoc`. Este arquivo é um índice rápido.

**Base URL** (produção): `https://nucleo-juridico-backend.onrender.com`
**Autenticação**: Bearer token JWT do Supabase no header `Authorization: Bearer <token>`.

---

## Convenções

- **Status HTTP**: `200` (sucesso), `201` (criado), `204` (sem conteúdo), `400`/`409`/`422` (cliente), `401` (sem auth), `403` (proibido), `404` (não encontrado), `500` (erro).
- **Erros**: sempre JSON `{ "detail": "mensagem em português" }`.
- **Datas**: ISO 8601 (`2026-05-21T15:30:00Z`).
- **UUIDs**: v4.

### Perfis

- `ALUNO` = `aluno_estagiario`
- `PROFESSOR` = `professor_orientador`
- `ADMIN` = `admin_coordenacao`

---

## `/auth`

| Método | Rota | Auth | Acesso |
|---|---|---|---|
| POST | `/auth/login` | público | Todos |
| POST | `/auth/register` | público | Cria usuário com role `aluno_estagiario` |
| POST | `/auth/logout` | Bearer | Todos os logados |
| GET | `/auth/me` | Bearer | Todos os logados |

---

## `/users`

Endpoints existentes (mantidos por compatibilidade). Para administração, prefira `/admin/users`.

| Método | Rota | Acesso |
|---|---|---|
| GET | `/users` | ADMIN |
| POST | `/users` | ADMIN |
| GET | `/users/{id}` | ADMIN ou o próprio usuário |
| PATCH | `/users/{id}` | ADMIN ou o próprio usuário (não-admin não muda `role`) |
| PATCH | `/users/{id}/status` | ADMIN |

---

## `/clients`

| Método | Rota | Acesso |
|---|---|---|
| GET | `/clients` | Logados. Filtros: `search`, `cpf`, `phone`, `city`, `status`, `limit`, `offset` |
| POST | `/clients` | ALUNO ou ADMIN |
| GET | `/clients/{id}` | Logados |
| PATCH | `/clients/{id}` | ALUNO ou ADMIN |
| DELETE | `/clients/{id}` | ADMIN — soft-delete (`status='inativo'`) |
| GET | `/clients/{id}/history` | Logados (escopo automático por perfil) |
| GET | `/clients/{id}/documents` | Logados |

---

## `/attendances`

| Método | Rota | Acesso |
|---|---|---|
| GET | `/attendances` | Logados. Filtros: `status`, `legal_area_id`, `demand_type_id`, `student_id`, `teacher_id`, `client_id`, `urgency`, `from`, `to`, `search`, `limit`, `offset` |
| POST | `/attendances` | ALUNO ou ADMIN |
| GET | `/attendances/{id}` | Logados |
| PATCH | `/attendances/{id}` | ALUNO (se não finalizado) ou ADMIN |
| PATCH | `/attendances/{id}/status` | Conforme regra: aluno se não finalizado, professor se atribuído, admin sempre |
| POST | `/attendances/{id}/send-to-teacher` | ALUNO ou ADMIN. Exige `teacher_id` |
| GET | `/attendances/{id}/history` | Logados (escopo automático) |

### `/attendances/{id}/triage`

| Método | Rota | Acesso |
|---|---|---|
| POST | `/attendances/{id}/triage` | ALUNO ou ADMIN (atendimento não finalizado). 409 se já existe |
| GET | `/attendances/{id}/triage` | Logados. 404 se não criada |
| PATCH | `/attendances/{id}/triage` | ALUNO ou ADMIN (atendimento não finalizado) |

### `/attendances/{id}/orientation`

| Método | Rota | Acesso |
|---|---|---|
| POST | `/attendances/{id}/orientation` | PROFESSOR (só nos seus) ou ADMIN |
| GET | `/attendances/{id}/orientations` | Logados |

---

## `/teacher/cases`

| Método | Rota | Acesso |
|---|---|---|
| GET | `/teacher/cases` | PROFESSOR (filtrado por `teacher_id=self.id`) ou ADMIN (todos). Filtros: `search`, `legal_area_id`, `student_id`, `urgency`, `from`, `to`, `include_finished` |
| GET | `/teacher/cases/{id}` | PROFESSOR (se atribuído) ou ADMIN |

## `/orientations/{id}`

| Método | Rota | Acesso |
|---|---|---|
| PATCH | `/orientations/{id}` | PROFESSOR (só as próprias) ou ADMIN. **Decisão é imutável** — só edita texto/notas |

---

## `/attendances/{id}/documents` e `/clients/{id}/documents` e `/documents/{id}`

| Método | Rota | Acesso |
|---|---|---|
| GET | `/attendances/{id}/documents` | Logados |
| POST | `/attendances/{id}/documents` (multipart) | ALUNO ou ADMIN. Limite 10MB, MIME permitidos: PDF, JPG, PNG, WebP, DOC/DOCX |
| GET | `/clients/{id}/documents` | Logados |
| GET | `/documents/{id}` | Logados |
| PATCH | `/documents/{id}/status` | ALUNO ou ADMIN |
| DELETE | `/documents/{id}` | ADMIN — soft-delete + remove arquivo do Storage |

---

## `/appointments`

| Método | Rota | Acesso |
|---|---|---|
| GET | `/appointments` | Logados (escopo automático). Filtros: `from`, `to`, `responsible_id`, `status`, `client_id` |
| POST | `/appointments` | ALUNO, PROFESSOR ou ADMIN |
| GET | `/appointments/{id}` | Logados (com escopo) |
| PATCH | `/appointments/{id}` | Responsável, vinculado ao caso, ou ADMIN. Mudança de data/hora → status `remarcado` |
| PATCH | `/appointments/{id}/status` | Mesma regra |
| DELETE | `/appointments/{id}` | Mesma regra. Hard-delete se avulso, soft (`status='cancelado'`) se vinculado |

---

## `/catalogs`

Catálogos auxiliares somente-leitura (para os selects do frontend).

| Método | Rota | Acesso |
|---|---|---|
| GET | `/catalogs/legal-areas` | Logados |
| GET | `/catalogs/demand-types?legal_area_id=...` | Logados |
| GET | `/catalogs/teachers` | Logados |
| GET | `/catalogs/students` | Logados |

---

## `/dashboard` e `/reports`

Todos com escopo automático por perfil: aluno só vê `student_id=self`, professor `teacher_id=self`, admin tudo. Admin pode passar `student_id`/`teacher_id` para filtrar.

| Método | Rota |
|---|---|
| GET | `/dashboard` |
| GET | `/reports/summary` |
| GET | `/reports/by-status` |
| GET | `/reports/by-area` |
| GET | `/reports/by-student` |
| GET | `/reports/by-teacher` |
| GET | `/reports/pending-documents` |
| GET | `/reports/pending-teacher-analysis` |

Filtros aceitos (variam por endpoint): `from`, `to`, `legal_area_id`, `student_id`, `teacher_id`.

---

## `/admin/*` (somente ADMIN)

Router com `Depends(require_admin)` no nível do router — todas as rotas retornam **403** para qualquer perfil que não seja `admin_coordenacao`.

### Usuários

| Método | Rota |
|---|---|
| GET | `/admin/users` |
| POST | `/admin/users` (cria conta Supabase Auth + profile) |
| GET | `/admin/users/{id}` |
| PATCH | `/admin/users/{id}` (pode alterar role) |
| PATCH | `/admin/users/{id}/status` |

### Áreas jurídicas

| Método | Rota |
|---|---|
| GET | `/admin/legal-areas` (inclui inativas) |
| POST | `/admin/legal-areas` |
| PATCH | `/admin/legal-areas/{id}` |

### Tipos de demanda

| Método | Rota |
|---|---|
| GET | `/admin/demand-types?legal_area_id=...` |
| POST | `/admin/demand-types` |
| PATCH | `/admin/demand-types/{id}` |

---

## `/health`

| Método | Rota | Acesso |
|---|---|---|
| GET | `/health` | público — usado pelo Render para liveness |

---

## Como autenticar uma chamada

```bash
# 1) login (sem auth)
curl -X POST https://nucleo-juridico-backend.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@ites.edu.br","password":"Admin@1234"}'
# → retorna {"access_token": "...", "user": {...}, ...}

# 2) chamar rota protegida
curl https://nucleo-juridico-backend.onrender.com/dashboard \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```
