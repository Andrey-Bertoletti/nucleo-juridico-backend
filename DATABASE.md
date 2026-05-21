# DATABASE.md — Schema e Migrations

Documentação do banco de dados PostgreSQL (Supabase).

---

## Migrations

8 migrations em `supabase/migrations/`, aplicadas em ordem alfabética/cronológica.

| Migration | O que faz |
|---|---|
| `20260520000001_initial_schema.sql` | Cria as 10 tabelas, índices, FKs, função `set_updated_at()` e triggers. |
| `20260520000002_seed_legal_areas.sql` | Insere 10 áreas do direito iniciais. |
| `20260520000003_seed_demand_types.sql` | Insere 46 tipos de demanda distribuídos pelas áreas. |
| `20260520000004_add_client_status_and_history.sql` | Adiciona `clients.status` ('ativo'/'inativo') para soft-delete e cria a tabela `client_history` (append-only). |
| `20260520000005_attendance_status_update.sql` | Substitui o vocabulário de `attendances.status` pelos 10 status do fluxo NPJ e adiciona coluna `notes`. |
| `20260520000006_documents_taxonomy_update.sql` | Atualiza `documents.document_type` para 7 tipos consolidados e `documents.status` para `entregue`/`pendente`/`removido`; adiciona `notes`. |
| `20260520000007_orientations_decisions_update.sql` | Substitui `orientations.decision` pelas 4 decisões do professor. |
| `20260520000008_appointments_status_update.sql` | Renomeia `realizado` → `compareceu` em `appointments.status`. |

Como aplicar:

```bash
supabase db push   # remoto (depois de `supabase link`)
supabase db reset  # local (recria + roda migrations)
```

Ou cole cada `.sql` no **SQL Editor** do Supabase Studio na ordem.

---

## Tabelas

### `profiles`
Perfis internos ligados a `auth.users` do Supabase.

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | uuid PK | |
| `user_id` | uuid unique | FK lógica para `auth.users.id` (cascade delete) |
| `name` | text | |
| `email` | text unique | |
| `role` | text | `aluno_estagiario` \| `professor_orientador` \| `admin_coordenacao` |
| `status` | text | `ativo` \| `inativo` \| `bloqueado` |
| `created_at`/`updated_at` | timestamptz | |

### `clients`
Cadastro de assistidos.

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | uuid PK | |
| `full_name` | text not null | |
| `cpf` | text unique | nullable — validado com dígitos verificadores |
| `rg`, `birth_date`, `phone`, `email` | | opcionais |
| `address`, `district`, `city`, `state` | | endereço |
| `marital_status` | text | enum aberto |
| `profession`, `family_income`, `notes` | | perfil socioeconômico |
| `status` | text | `ativo` \| `inativo` (soft-delete) |
| `created_at`/`updated_at` | timestamptz | |

### `client_history`
Auditoria do cadastro do cliente. **Append-only**.

| Coluna | Tipo |
|---|---|
| `id`, `client_id`, `user_id` | uuid |
| `event_type` | text — `criacao` \| `atualizacao` \| `desativacao` \| `reativacao` \| `observacao` |
| `description` | text |
| `changes` | jsonb — diff `{from, to}` por campo |
| `created_at` | timestamptz |

### `legal_areas`
Taxonomia de áreas do direito (10 seeds iniciais).

### `demand_types`
Tipos de demanda. FK para `legal_areas`; único por `(legal_area_id, name)`.

### `attendances`
Caso jurídico — centro do sistema.

| Coluna | Tipo | Observação |
|---|---|---|
| `id`, `client_id`, `legal_area_id`, `demand_type_id`, `student_id`, `teacher_id` | uuid | FKs |
| `description`, `notes` | text | |
| `urgency` | bool | |
| `status` | text | Veja tabela de status abaixo |
| `finished_at` | timestamptz | preenchido em `finalizado`/`arquivado` |

#### Status do atendimento

| Valor | Etapa |
|---|---|
| `novo_atendimento` | Recém-aberto |
| `em_triagem` | Triagem em andamento |
| `aguardando_documentos` | Cliente precisa trazer documentos |
| `encaminhado_ao_professor` | Aguardando análise |
| `em_analise_pelo_professor` | Professor analisando |
| `correcao_solicitada` | Devolvido ao aluno |
| `aguardando_retorno_cliente` | Cliente precisa voltar |
| `encaminhamento_aprovado` | Aprovado pelo professor |
| `finalizado` | Encerrado |
| `arquivado` | Arquivado |

### `triages`
Ficha de triagem 1:1 com `attendances` (`attendance_id` unique).

| Coluna | Observação |
|---|---|
| `client_report` | obrigatório (relato do cliente) |
| `has_urgent_deadline` | bool |
| `urgency_description` | obrigatório se `has_urgent_deadline=true` |
| `presented_documents`, `pending_documents`, `suggested_forwarding`, `student_notes` | texto livre |

### `documents`
Metadados de documentos do Supabase Storage.

| Coluna | Observação |
|---|---|
| `client_id`, `attendance_id` | FKs nullable (mas pelo menos um deve estar preenchido) |
| `document_type` | `rg` \| `cpf` \| `comprovante_residencia` \| `comprovante_renda` \| `certidao` \| `documento_caso` \| `outros` |
| `file_name`, `storage_path` | sempre preenchidos |
| `file_url` | **NULL no banco** — gerado on-demand como signed URL pelo backend |
| `status` | `entregue` \| `pendente` \| `removido` |
| `uploaded_by` | FK para `profiles` |

### `orientations`
Orientações do professor.

| Coluna | Observação |
|---|---|
| `attendance_id`, `teacher_id` | FKs |
| `orientation_text` | obrigatório |
| `teacher_notes` | opcional |
| `decision` | `solicitar_correcao` \| `solicitar_documentos` \| `aprovar_encaminhamento` \| `finalizar_atendimento` (nullable — orientação pode não ter decisão) |

### `appointments`
Agenda de retornos.

| Coluna | Observação |
|---|---|
| `client_id` | obrigatório |
| `attendance_id` | opcional — se preenchido, evento entra no histórico do atendimento |
| `responsible_id` | FK para `profiles` |
| `appointment_date`, `appointment_time` | data e hora separadas |
| `reason`, `notes` | texto livre |
| `status` | `agendado` \| `confirmado` \| `compareceu` \| `nao_compareceu` \| `remarcado` \| `cancelado` |

### `attendance_history`
Linha do tempo de cada atendimento. **Append-only**.

| Coluna | Observação |
|---|---|
| `attendance_id`, `user_id` | FKs |
| `event_type` | 13 valores possíveis (abertura, triagem, orientacao, encaminhamento, documento_*, agendamento, retorno, mudanca_status, observacao, encerramento, arquivamento) |
| `description` | texto humanizado |
| `old_status`, `new_status` | preenchidos quando o evento envolve mudança |

---

## Relacionamentos chave

```
auth.users ←─ profiles
                │
                ├─→ attendances (student_id)
                ├─→ attendances (teacher_id)
                ├─→ orientations (teacher_id)
                ├─→ appointments (responsible_id)
                ├─→ documents (uploaded_by)
                └─→ attendance_history (user_id)

clients ─→ attendances
        └─→ documents
        └─→ appointments
        └─→ client_history

attendances ─→ triages (1:1)
            ─→ documents (n)
            ─→ orientations (n)
            ─→ appointments (n)
            ─→ attendance_history (append-only)

legal_areas ─→ demand_types
            └─→ attendances

attendances.legal_area_id ─→ legal_areas
attendances.demand_type_id ─→ demand_types
```

---

## Estratégia de soft-delete

| Tabela | Como deleta |
|---|---|
| `clients` | `status='inativo'` + entrada em `client_history` |
| `attendances` | `status='finalizado'` ou `'arquivado'` + `finished_at` |
| `documents` | `status='removido'` + arquivo apagado do Storage (best-effort) |
| `appointments` | Hard-delete se for avulso; soft (`status='cancelado'`) se vinculado a atendimento |
| `profiles` | `status='inativo'` ou `'bloqueado'` |
| `legal_areas` / `demand_types` | `status='inativo'` (esconde dos selects do front, preserva o histórico) |

---

## Histórico append-only

Tabelas `attendance_history` e `client_history` **só recebem INSERT**. Não há endpoints de update/delete e o frontend não tem formulários de edição. Para uso em produção, recomenda-se também criar uma **RLS policy** que negue UPDATE/DELETE no `public.*_history` (mesmo via service-role).

---

## RLS (Row Level Security)

Atualmente RLS **não está habilitada** porque toda comunicação com o banco passa pelo backend (com service-role). Se você quiser expor o banco diretamente ao frontend via supabase-js, é obrigatório habilitar RLS e criar policies — não faça isso sem essa etapa.

---

## Backups

- O Supabase faz backup diário automático (plano free retém 7 dias).
- Para uso real, configure backup adicional via `pg_dump` agendado.

---

## Seeds iniciais

- 10 áreas do direito (Civil, Família, Consumidor, Trabalhista, Previdenciário, Penal, Administrativo, Tributário, Imobiliário, Sucessório)
- 46 tipos de demanda distribuídos pelas áreas
- Usuários administrativos via `scripts/seed_users.py` (não está em SQL — usa a admin API do Supabase Auth para gerar a senha hash corretamente)
