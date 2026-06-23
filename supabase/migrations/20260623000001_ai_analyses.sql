-- =============================================================================
-- IA — Análise com IA (Fase 1): tabela de cache `ai_analyses`
-- =============================================================================
-- Guarda o resultado de cada ação de IA (resumo, prazos, partes, ...) por
-- documento, e a Análise Geral por cliente. O cache evita reprocessar/repagar.
-- A invalidação é feita pela coluna `source_hash` (recalculada quando o
-- documento muda ou um novo é anexado).
-- =============================================================================

create table public.ai_analyses (
  id              uuid primary key default gen_random_uuid(),
  scope           text not null
                  check (scope in ('document', 'client')),
  document_id     uuid
                  references public.documents(id) on delete cascade,
  client_id       uuid
                  references public.clients(id) on delete cascade,
  action          text not null
                  check (action in ('resumo',
                                    'pontos_chave',
                                    'prazos',
                                    'partes',
                                    'valores',
                                    'detalhes',
                                    'riscos',
                                    'classificacao',
                                    'analise_geral')),
  status          text not null default 'processando'
                  check (status in ('processando', 'pronto', 'erro')),
  result_text     text,
  result_data     jsonb,
  extracted_text  text,
  model_used      text,
  tokens_input    integer,
  tokens_output   integer,
  error_message   text,
  source_hash     text,
  created_by      uuid
                  references public.profiles(id) on delete set null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

comment on table public.ai_analyses is
  'Cache de análises de IA (Fase 1). Uma linha por (documento, ação) ou (cliente, análise geral).';

create index idx_ai_analyses_document_id on public.ai_analyses(document_id);
create index idx_ai_analyses_client_id   on public.ai_analyses(client_id);

-- Unicidade por escopo: 1 análise por (documento, ação) e por (cliente, ação).
create unique index uq_ai_analyses_document_action
  on public.ai_analyses(document_id, action)
  where scope = 'document';

create unique index uq_ai_analyses_client_action
  on public.ai_analyses(client_id, action)
  where scope = 'client';

-- Mantém `updated_at` em dia (reusa a função criada no schema inicial).
create trigger trg_ai_analyses_set_updated_at
  before update on public.ai_analyses
  for each row execute function public.set_updated_at();
