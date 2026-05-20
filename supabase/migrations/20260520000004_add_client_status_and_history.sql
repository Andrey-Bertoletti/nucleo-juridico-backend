-- =============================================================================
-- Clientes: adiciona `status` e cria tabela de histórico do cliente
-- =============================================================================
-- - `clients.status` ('ativo'/'inativo') habilita soft-delete via DELETE.
-- - `client_history` é append-only e armazena diffs em jsonb.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1) Status do cliente
-- -----------------------------------------------------------------------------
alter table public.clients
  add column status text not null default 'ativo'
  check (status in ('ativo', 'inativo'));

create index idx_clients_status on public.clients(status);

-- -----------------------------------------------------------------------------
-- 2) Histórico do cliente (append-only)
-- -----------------------------------------------------------------------------
create table public.client_history (
  id           uuid primary key default gen_random_uuid(),
  client_id    uuid not null
               references public.clients(id) on delete cascade,
  user_id      uuid
               references public.profiles(id) on delete set null,
  event_type   text not null
               check (event_type in ('criacao',
                                     'atualizacao',
                                     'desativacao',
                                     'reativacao',
                                     'observacao')),
  description  text,
  changes      jsonb,
  created_at   timestamptz not null default now()
);

comment on table public.client_history is
  'Linha do tempo do cadastro do cliente: criação, alterações, desativações.';

create index idx_client_history_client_id  on public.client_history(client_id);
create index idx_client_history_created_at on public.client_history(created_at desc);
