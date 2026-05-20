-- =============================================================================
-- Sistema de Gestão de Atendimento Jurídico — schema inicial
-- =============================================================================
-- Cria todas as tabelas do MVP com:
--   * chaves estrangeiras
--   * índices básicos
--   * constraints de status (CHECK)
--   * trigger para manter `updated_at` atualizado
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Extensões
-- -----------------------------------------------------------------------------
create extension if not exists "pgcrypto";  -- para gen_random_uuid()

-- -----------------------------------------------------------------------------
-- Função utilitária: atualiza `updated_at` antes do UPDATE
-- -----------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- =============================================================================
-- 1) profiles — perfis internos vinculados ao auth.users do Supabase
-- =============================================================================
create table public.profiles (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null unique
              references auth.users(id) on delete cascade,
  name        text not null,
  email       text not null unique,
  role        text not null
              check (role in ('aluno_estagiario',
                              'professor_orientador',
                              'admin_coordenacao')),
  status      text not null default 'ativo'
              check (status in ('ativo', 'inativo', 'bloqueado')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

comment on table public.profiles is
  'Perfis de usuários internos (aluno, professor, coordenação) vinculados ao auth.users do Supabase.';

create index idx_profiles_user_id on public.profiles(user_id);
create index idx_profiles_role    on public.profiles(role);
create index idx_profiles_status  on public.profiles(status);

create trigger trg_profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- =============================================================================
-- 2) clients — assistidos/clientes do núcleo
-- =============================================================================
create table public.clients (
  id              uuid primary key default gen_random_uuid(),
  full_name       text not null,
  cpf             text unique,
  rg              text,
  birth_date      date,
  phone           text,
  email           text,
  address         text,
  district        text,
  city            text,
  state           text
                  check (state is null or char_length(state) = 2),
  marital_status  text
                  check (marital_status is null
                         or marital_status in ('solteiro',
                                               'casado',
                                               'divorciado',
                                               'viuvo',
                                               'uniao_estavel',
                                               'separado')),
  profession      text,
  family_income   numeric(12,2)
                  check (family_income is null or family_income >= 0),
  notes           text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table public.clients is
  'Cadastro de assistidos/clientes do núcleo jurídico.';

create index idx_clients_full_name on public.clients(full_name);
create index idx_clients_cpf       on public.clients(cpf);
create index idx_clients_city      on public.clients(city);

create trigger trg_clients_set_updated_at
  before update on public.clients
  for each row execute function public.set_updated_at();

-- =============================================================================
-- 3) legal_areas — áreas do direito (taxonomia)
-- =============================================================================
create table public.legal_areas (
  id          uuid primary key default gen_random_uuid(),
  name        text not null unique,
  status      text not null default 'ativo'
              check (status in ('ativo', 'inativo')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

comment on table public.legal_areas is
  'Áreas do direito disponíveis para classificação de atendimentos.';

create index idx_legal_areas_status on public.legal_areas(status);

create trigger trg_legal_areas_set_updated_at
  before update on public.legal_areas
  for each row execute function public.set_updated_at();

-- =============================================================================
-- 4) demand_types — tipos de demanda dentro de cada área
-- =============================================================================
create table public.demand_types (
  id             uuid primary key default gen_random_uuid(),
  legal_area_id  uuid not null
                 references public.legal_areas(id) on delete restrict,
  name           text not null,
  status         text not null default 'ativo'
                 check (status in ('ativo', 'inativo')),
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  unique (legal_area_id, name)
);

comment on table public.demand_types is
  'Tipos de demanda jurídica (ex.: divórcio, cobrança, aposentadoria) agrupados por área.';

create index idx_demand_types_legal_area_id on public.demand_types(legal_area_id);
create index idx_demand_types_status        on public.demand_types(status);

create trigger trg_demand_types_set_updated_at
  before update on public.demand_types
  for each row execute function public.set_updated_at();

-- =============================================================================
-- 5) attendances — fichas de atendimento
-- =============================================================================
create table public.attendances (
  id              uuid primary key default gen_random_uuid(),
  client_id       uuid not null
                  references public.clients(id) on delete restrict,
  legal_area_id   uuid
                  references public.legal_areas(id) on delete set null,
  demand_type_id  uuid
                  references public.demand_types(id) on delete set null,
  student_id      uuid
                  references public.profiles(id) on delete set null,
  teacher_id      uuid
                  references public.profiles(id) on delete set null,
  description     text,
  urgency         boolean not null default false,
  status          text not null default 'aberto'
                  check (status in ('aberto',
                                    'em_triagem',
                                    'aguardando_orientacao',
                                    'em_andamento',
                                    'aguardando_documentos',
                                    'encerrado',
                                    'arquivado')),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  finished_at     timestamptz,
  check (finished_at is null or finished_at >= created_at)
);

comment on table public.attendances is
  'Fichas de atendimento — vinculam cliente, área, aluno e professor responsáveis.';

create index idx_attendances_client_id      on public.attendances(client_id);
create index idx_attendances_legal_area_id  on public.attendances(legal_area_id);
create index idx_attendances_demand_type_id on public.attendances(demand_type_id);
create index idx_attendances_student_id     on public.attendances(student_id);
create index idx_attendances_teacher_id     on public.attendances(teacher_id);
create index idx_attendances_status         on public.attendances(status);
create index idx_attendances_urgency        on public.attendances(urgency)
  where urgency = true;

create trigger trg_attendances_set_updated_at
  before update on public.attendances
  for each row execute function public.set_updated_at();

-- =============================================================================
-- 6) triages — triagem inicial associada a um atendimento (1:1)
-- =============================================================================
create table public.triages (
  id                    uuid primary key default gen_random_uuid(),
  attendance_id         uuid not null unique
                        references public.attendances(id) on delete cascade,
  client_report         text,
  has_urgent_deadline   boolean not null default false,
  urgency_description   text,
  presented_documents   text,
  pending_documents     text,
  suggested_forwarding  text,
  student_notes         text,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);

comment on table public.triages is
  'Triagem do atendimento: relato do cliente, prazos urgentes e encaminhamento sugerido.';

create index idx_triages_attendance_id on public.triages(attendance_id);

create trigger trg_triages_set_updated_at
  before update on public.triages
  for each row execute function public.set_updated_at();

-- =============================================================================
-- 7) documents — documentos do caso, armazenados no Supabase Storage
-- =============================================================================
create table public.documents (
  id             uuid primary key default gen_random_uuid(),
  client_id      uuid
                 references public.clients(id) on delete cascade,
  attendance_id  uuid
                 references public.attendances(id) on delete cascade,
  document_type  text not null
                 check (document_type in ('rg',
                                          'cpf',
                                          'comprovante_residencia',
                                          'comprovante_renda',
                                          'procuracao',
                                          'peticao',
                                          'contrato',
                                          'sentenca',
                                          'outros')),
  file_name      text not null,
  file_url       text,
  storage_path   text not null,
  status         text not null default 'pendente'
                 check (status in ('pendente',
                                   'aprovado',
                                   'rejeitado',
                                   'arquivado')),
  uploaded_by    uuid
                 references public.profiles(id) on delete set null,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  check (client_id is not null or attendance_id is not null)
);

comment on table public.documents is
  'Metadados de documentos do caso. Arquivos físicos ficam no Supabase Storage (storage_path).';

create index idx_documents_client_id      on public.documents(client_id);
create index idx_documents_attendance_id  on public.documents(attendance_id);
create index idx_documents_document_type  on public.documents(document_type);
create index idx_documents_status         on public.documents(status);
create index idx_documents_uploaded_by    on public.documents(uploaded_by);

create trigger trg_documents_set_updated_at
  before update on public.documents
  for each row execute function public.set_updated_at();

-- =============================================================================
-- 8) orientations — orientações do professor sobre o atendimento
-- =============================================================================
create table public.orientations (
  id                uuid primary key default gen_random_uuid(),
  attendance_id     uuid not null
                    references public.attendances(id) on delete cascade,
  teacher_id        uuid
                    references public.profiles(id) on delete set null,
  orientation_text  text not null,
  teacher_notes     text,
  decision          text
                    check (decision is null
                           or decision in ('aprovar',
                                           'revisar',
                                           'encaminhar',
                                           'arquivar',
                                           'aguardar_documentos')),
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

comment on table public.orientations is
  'Registros de orientação do professor para um atendimento (n por atendimento).';

create index idx_orientations_attendance_id on public.orientations(attendance_id);
create index idx_orientations_teacher_id    on public.orientations(teacher_id);
create index idx_orientations_decision      on public.orientations(decision);

create trigger trg_orientations_set_updated_at
  before update on public.orientations
  for each row execute function public.set_updated_at();

-- =============================================================================
-- 9) appointments — agenda de retornos / atendimentos futuros
-- =============================================================================
create table public.appointments (
  id                uuid primary key default gen_random_uuid(),
  client_id         uuid not null
                    references public.clients(id) on delete cascade,
  attendance_id     uuid
                    references public.attendances(id) on delete set null,
  responsible_id    uuid
                    references public.profiles(id) on delete set null,
  appointment_date  date not null,
  appointment_time  time,
  reason            text,
  status            text not null default 'agendado'
                    check (status in ('agendado',
                                      'confirmado',
                                      'realizado',
                                      'cancelado',
                                      'remarcado',
                                      'nao_compareceu')),
  notes             text,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

comment on table public.appointments is
  'Agendamentos de retorno do cliente — vinculados a um atendimento quando aplicável.';

create index idx_appointments_client_id        on public.appointments(client_id);
create index idx_appointments_attendance_id    on public.appointments(attendance_id);
create index idx_appointments_responsible_id   on public.appointments(responsible_id);
create index idx_appointments_appointment_date on public.appointments(appointment_date);
create index idx_appointments_status           on public.appointments(status);

create trigger trg_appointments_set_updated_at
  before update on public.appointments
  for each row execute function public.set_updated_at();

-- =============================================================================
-- 10) attendance_history — histórico/auditoria do ciclo de vida do atendimento
-- =============================================================================
create table public.attendance_history (
  id             uuid primary key default gen_random_uuid(),
  attendance_id  uuid not null
                 references public.attendances(id) on delete cascade,
  user_id        uuid
                 references public.profiles(id) on delete set null,
  event_type     text not null
                 check (event_type in ('abertura',
                                       'triagem',
                                       'orientacao',
                                       'encaminhamento',
                                       'documento_adicionado',
                                       'documento_aprovado',
                                       'documento_rejeitado',
                                       'agendamento',
                                       'retorno',
                                       'mudanca_status',
                                       'observacao',
                                       'encerramento',
                                       'arquivamento')),
  description    text,
  old_status     text,
  new_status     text,
  created_at     timestamptz not null default now()
);

comment on table public.attendance_history is
  'Linha do tempo do atendimento: cada evento gera uma linha imutável (append-only).';

create index idx_attendance_history_attendance_id on public.attendance_history(attendance_id);
create index idx_attendance_history_user_id       on public.attendance_history(user_id);
create index idx_attendance_history_event_type    on public.attendance_history(event_type);
create index idx_attendance_history_created_at    on public.attendance_history(created_at desc);

-- (sem trigger de updated_at — tabela append-only)
