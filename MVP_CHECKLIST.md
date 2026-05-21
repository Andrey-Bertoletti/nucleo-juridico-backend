# MVP_CHECKLIST.md — Sistema de Gestão de Atendimento Jurídico

Checklist do MVP entregue. Use para validar antes da apresentação.

---

## 1. Banco de dados

- [x] 10 tabelas criadas via migrations Supabase
- [x] 8 migrations versionadas em `supabase/migrations/`
- [x] FKs, índices, check constraints aplicados
- [x] Trigger `set_updated_at()` ativo em todas as tabelas com `updated_at`
- [x] Seeds iniciais: 10 áreas + 46 tipos de demanda
- [x] Script `seed_users.py` para criar admin + professor de exemplo
- [x] Bucket `documentos` no Supabase Storage (privado)

## 2. Autenticação e perfis

- [x] Login via Supabase Auth (email + senha)
- [x] Cadastro de usuário com role default `aluno_estagiario`
- [x] Recuperação de senha (UI — endpoint a wirar quando necessário)
- [x] JWT validado no backend suportando HS256 e ES256/RS256 (JWKS)
- [x] 3 perfis: aluno, professor, admin
- [x] Dependências `require_admin`, `require_teacher`, `require_student`
- [x] Rotas `/admin/*` com guarda no nível do router
- [x] Frontend esconde itens do menu por perfil
- [x] `AccessDenied` em rotas restritas (casos-analise, admin/*, criação de clientes)

## 3. Clientes / Assistidos

- [x] CRUD completo
- [x] Validação real de CPF (dígitos verificadores) backend + frontend
- [x] Validação de RG, telefone (DDD), data de nascimento, UF
- [x] Soft-delete (`status='inativo'`)
- [x] Histórico `client_history` com diff de mudanças
- [x] Página com busca, filtros e abas (Dados, Atendimentos, Documentos, Histórico)
- [x] Máscaras CPF e telefone

## 4. Atendimentos

- [x] 10 status do fluxo NPJ
- [x] CRUD com escopo por perfil
- [x] Botão "Encaminhar ao professor"
- [x] Bloqueio de edição quando finalizado
- [x] Tabs no detalhe (Resumo, Triagem, Documentos, Orientações, Histórico)
- [x] Chips de filtros rápidos (Urgentes, Em triagem, Aguardando docs, Encaminhados, Meus, Sob minha orientação)
- [x] Histórico granular automático

## 5. Triagem

- [x] Formulário com 7 campos
- [x] Validação: `client_report` obrigatório
- [x] Validação: `urgency_description` obrigatório se `has_urgent_deadline=true`
- [x] 3 ações: Salvar rascunho / Salvar triagem / Encaminhar ao professor
- [x] Alertas visuais para urgência e documentos pendentes
- [x] Modo somente-leitura para professor e quando atendimento finalizado

## 6. Documentos

- [x] Upload no Supabase Storage (bucket privado)
- [x] Signed URLs com TTL de 1h geradas on-demand
- [x] Validação MIME + tamanho máx 10MB
- [x] 7 tipos de documento, 3 status
- [x] Soft-delete + remoção do arquivo no Storage (admin)
- [x] Página `/documentos` lista clientes (entrada por cliente)
- [x] Modal de upload com loading e validação client-side
- [x] Busca interna por nome/observação + filtro por tipo

## 7. Orientação do professor

- [x] Fila `/casos-analise` com filtros
- [x] Tela única de análise (`/casos-analise/[id]`) com cliente + atendimento + triagem + documentos + histórico + orientações + formulário
- [x] 4 decisões que disparam transição de status
- [x] Botões "Salvar orientação" (sem decisão) e "Confirmar decisão" (com)
- [x] Aba "Orientações" no atendimento com mesmo form para outros perfis

## 8. Agenda de retornos

- [x] Toggle Lista / Calendário
- [x] Calendário mensal 7×6 com pontos coloridos por status
- [x] Drawer com retornos do dia ao clicar
- [x] Filtros: data, responsável, status
- [x] CRUD + 4 ações rápidas (Confirmar / Compareceu / Não compareceu / Cancelar)
- [x] Remarcação com mudança automática para status `remarcado`
- [x] Soft-delete se vinculado a atendimento, hard-delete se avulso

## 9. Dashboard

- [x] Variante por perfil:
  - Aluno: meus atendimentos, retornos hoje, urgentes, aguardando documentos
  - Professor: casos para análise, urgentes, retornos hoje, finalizados
  - Admin: total, urgentes, aguardando docs, em análise + gráficos por status e área

## 10. Relatórios

- [x] 4 cards de KPI
- [x] Gráfico de barras por status
- [x] Gráfico de barras por área jurídica
- [x] Tabela de produtividade por aluno
- [x] Tabela de produtividade por professor
- [x] Filtros: período, área, status, aluno, professor
- [x] Exportar PDF / Excel (placeholders com alert — feature futura)

## 11. Administração (admin only)

- [x] Hub `/administracao` com cards para os 3 módulos
- [x] CRUD de usuários (`/admin/usuarios`) com busca, filtros e modal de confirmação
- [x] CRUD de áreas jurídicas com criação inline + toggle ativo/inativo
- [x] CRUD de tipos de demanda com seletor de área + criação inline
- [x] Validação de duplicidade (nome único de área; nome único por área em tipos)

## 12. Histórico e auditoria

- [x] `attendance_history` com 13 tipos de evento
- [x] `client_history` com diff jsonb
- [x] Helper central `create_attendance_history_event()`
- [x] Componente `Timeline` reutilizável no frontend
- [x] `user_name` denormalizado nas respostas
- [x] Append-only — sem endpoints de update/delete

## 13. UX e visual

- [x] Branding NPJ-ITES (logo azul, paleta slate, tipografia)
- [x] Componentes UI: Button, Input, Select, Textarea, Card, Modal, Combobox (com busca)
- [x] Estados: LoadingState, EmptyState, AccessDenied
- [x] Badges de status (`StatusBadge`, `AttendanceStatusBadge`, `UrgencyBadge`, `AppointmentStatusBadge`)
- [x] Mensagens de sucesso (verde, auto-dismiss) e erro (vermelho, `role="alert"`)
- [x] Responsividade básica (grid + max-w-7xl mx-auto)
- [x] Validação de formulários com Zod + react-hook-form
- [x] Máscaras CPF e telefone aplicadas

## 14. Backend — qualidade e segurança

- [x] Todos os endpoints protegidos por auth (exceto `/auth/login`, `/auth/register`, `/health`)
- [x] Escopo automático por perfil em listagens e detalhes
- [x] Validações Pydantic com mensagens em português
- [x] Handler global de exceção (sem vazamento de stack trace em produção)
- [x] `DATABASE_URL` auto-corrige prefixo `+psycopg`
- [x] CORS configurável + regex para previews Vercel
- [x] Logs estruturados pela própria FastAPI
- [x] `.env.example` documentado

## 15. Frontend — qualidade

- [x] `npm run build` passa sem erros nem warnings críticos
- [x] Tipagens TypeScript em toda a aplicação
- [x] Sem console.error em produção
- [x] localStorage para token (limpo no logout)
- [x] Redirecionamento automático login ↔ dashboard
- [x] Erros amigáveis com `ApiError.detail`

## 16. Deploy

- [x] `render.yaml` configurado
- [x] `runtime.txt` fixando Python 3.12.5
- [x] `requirements.txt` com `pydantic[email]`, `pyjwt[crypto]`
- [x] Healthcheck em `/health`
- [x] Frontend roda em Vercel sem config extra
- [x] `NEXT_PUBLIC_API_BASE_URL` configurável

## 17. Documentação

- [x] README do backend
- [x] README do frontend
- [x] DEPLOY.md (este passo a passo)
- [x] DATABASE.md (schema completo)
- [x] API.md (endpoints + permissões)
- [x] PROJECT_SCOPE.md (escopo original)
- [x] MVP_CHECKLIST.md (este arquivo)
- [x] PRESENTATION.md (roteiro de apresentação)

---

## Fora do escopo do MVP (próximas iterações)

- Portal do assistido
- Assinatura eletrônica de documentos
- Integração com tribunais
- Calendário com sincronização Google Calendar
- Notificações por e-mail / WhatsApp
- Aplicativo mobile
- Export real PDF/Excel
- Multi-tenant (vários núcleos)
- Backup automatizado fora do Supabase
- Recuperação de senha (UI pronta, endpoint pendente)
