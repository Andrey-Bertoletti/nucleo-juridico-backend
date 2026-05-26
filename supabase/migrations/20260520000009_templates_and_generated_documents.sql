-- =============================================================================
-- Modelos de relatório / atendimento / documento + documentos gerados
-- =============================================================================
-- Adiciona:
--   * tabela `templates` — modelos reutilizáveis (relatorio/atendimento/documento)
--     com conteúdo + lista de campos dinâmicos.
--   * tabela `generated_documents` — versões preenchidas e prontas para impressão,
--     com identificação manual do aluno responsável (porque o login de aluno é
--     compartilhado entre estagiários).
--
-- Justificativa do `student_*` em `generated_documents`: o `generated_by_user_id`
-- guarda quem ESTAVA LOGADO (frequentemente o "aluno geral"), mas a auditoria
-- jurídica precisa saber QUE aluno realmente conduziu o atendimento — daí os
-- campos nome/matrícula/assinatura física (espaço no documento impresso).
-- =============================================================================

-- ---- templates --------------------------------------------------------------
create table if not exists public.templates (
  id            uuid primary key default gen_random_uuid(),
  title         varchar(200) not null,
  type          varchar(20) not null,
  content       text not null,
  dynamic_fields jsonb not null default '[]'::jsonb,
  status        varchar(10) not null default 'ativo',
  created_by    uuid references auth.users(id) on delete set null,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),

  constraint templates_type_check
    check (type in ('relatorio', 'atendimento', 'documento')),
  constraint templates_status_check
    check (status in ('ativo', 'inativo'))
);

create index if not exists templates_type_idx on public.templates (type);
create index if not exists templates_status_idx on public.templates (status);

-- Trigger pra `updated_at` (segue o padrão das outras tabelas do projeto).
create or replace function public.touch_templates_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists templates_touch_updated_at on public.templates;
create trigger templates_touch_updated_at
  before update on public.templates
  for each row execute function public.touch_templates_updated_at();


-- ---- generated_documents ---------------------------------------------------
create table if not exists public.generated_documents (
  id                    uuid primary key default gen_random_uuid(),
  template_id           uuid not null references public.templates(id) on delete restrict,
  template_type         varchar(20) not null,
  template_title        varchar(200) not null,

  generated_by_user_id  uuid references auth.users(id) on delete set null,

  -- ⚠ Identificação manual obrigatória do aluno responsável.
  student_name          varchar(200) not null,
  student_matricula     varchar(50)  not null,
  attendance_date       date not null,

  filled_data           jsonb not null default '{}'::jsonb,
  final_content         text  not null,

  attendance_id         uuid references public.attendances(id) on delete set null,
  client_id             uuid references public.clients(id)     on delete set null,

  generated_at          timestamptz not null default now(),

  constraint generated_documents_template_type_check
    check (template_type in ('relatorio', 'atendimento', 'documento'))
);

create index if not exists generated_documents_template_idx
  on public.generated_documents (template_id);
create index if not exists generated_documents_attendance_idx
  on public.generated_documents (attendance_id);
create index if not exists generated_documents_client_idx
  on public.generated_documents (client_id);
create index if not exists generated_documents_generated_at_idx
  on public.generated_documents (generated_at desc);


-- ---- atendimentos: identificação manual do aluno responsável ---------------
-- O `attendances.student_id` aponta pro profile do user logado (login geral).
-- Os campos abaixo guardam o aluno REAL que conduziu o atendimento.
alter table public.attendances
  add column if not exists responsible_student_name      varchar(200),
  add column if not exists responsible_student_matricula varchar(50);
