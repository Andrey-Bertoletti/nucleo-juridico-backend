-- =============================================================================
-- Documentos: atualiza taxonomia de `document_type` e `status`
-- =============================================================================
-- - Mapeia tipos antigos (procuracao/peticao/contrato/sentenca) para o novo
--   tipo consolidado `documento_caso`.
-- - Mapeia status antigos para o novo vocabulário (entregue/pendente/removido).
-- - Atualiza checks e default.
-- =============================================================================

-- ---- 1) document_type ------------------------------------------------------
alter table public.documents
  drop constraint if exists documents_document_type_check;

update public.documents
   set document_type = case document_type
     when 'procuracao' then 'documento_caso'
     when 'peticao'    then 'documento_caso'
     when 'contrato'   then 'documento_caso'
     when 'sentenca'   then 'documento_caso'
     else document_type
   end
 where document_type in ('procuracao', 'peticao', 'contrato', 'sentenca');

alter table public.documents
  add constraint documents_document_type_check
  check (document_type in (
    'rg',
    'cpf',
    'comprovante_residencia',
    'comprovante_renda',
    'certidao',
    'documento_caso',
    'outros'
  ));

-- ---- 2) status -------------------------------------------------------------
alter table public.documents alter column status drop default;

alter table public.documents
  drop constraint if exists documents_status_check;

update public.documents
   set status = case status
     when 'aprovado'  then 'entregue'
     when 'rejeitado' then 'removido'
     when 'arquivado' then 'removido'
     else status
   end
 where status in ('aprovado', 'rejeitado', 'arquivado');

alter table public.documents
  add constraint documents_status_check
  check (status in ('entregue', 'pendente', 'removido'));

alter table public.documents
  alter column status set default 'pendente';

-- ---- 3) coluna `notes` opcional para observação do upload ------------------
alter table public.documents
  add column if not exists notes text;
