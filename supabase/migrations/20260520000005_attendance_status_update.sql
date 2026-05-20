-- =============================================================================
-- Atendimentos: atualiza vocabulário de status e adiciona `notes`
-- =============================================================================
-- - Substitui o check constraint de `attendances.status` pelos novos valores.
-- - Migra dados existentes mapeando os status antigos para os novos.
-- - Adiciona a coluna `notes` (observações iniciais informadas no cadastro).
-- =============================================================================

-- 1) Remove a default antiga (`aberto` não existe mais no novo vocabulário).
alter table public.attendances alter column status drop default;

-- 2) Remove o check antigo (pode ser nomeado pelo Postgres como
--    `attendances_status_check` — usamos IF EXISTS para tolerar variações).
alter table public.attendances
  drop constraint if exists attendances_status_check;

-- 3) Migra valores existentes para o novo vocabulário.
update public.attendances
   set status = case status
     when 'aberto'                 then 'novo_atendimento'
     when 'aguardando_orientacao'  then 'encaminhado_ao_professor'
     when 'em_andamento'           then 'em_triagem'
     when 'encerrado'              then 'finalizado'
     else status
   end
 where status in (
   'aberto', 'aguardando_orientacao', 'em_andamento', 'encerrado'
 );

-- 4) Cria o novo check constraint.
alter table public.attendances
  add constraint attendances_status_check
  check (status in (
    'novo_atendimento',
    'em_triagem',
    'aguardando_documentos',
    'encaminhado_ao_professor',
    'em_analise_pelo_professor',
    'correcao_solicitada',
    'aguardando_retorno_cliente',
    'encaminhamento_aprovado',
    'finalizado',
    'arquivado'
  ));

-- 5) Define a nova default.
alter table public.attendances
  alter column status set default 'novo_atendimento';

-- 6) Coluna `notes` — observações iniciais informadas no cadastro.
alter table public.attendances
  add column if not exists notes text;
