-- =============================================================================
-- Agenda: atualiza o vocabulário de `status`
-- =============================================================================
-- - Substitui o check antigo que tinha 'realizado' por 'compareceu', mantendo
--   os demais status já existentes.
-- =============================================================================

alter table public.appointments alter column status drop default;

alter table public.appointments
  drop constraint if exists appointments_status_check;

update public.appointments
   set status = case status
     when 'realizado' then 'compareceu'
     else status
   end
 where status = 'realizado';

alter table public.appointments
  add constraint appointments_status_check
  check (status in (
    'agendado',
    'confirmado',
    'compareceu',
    'nao_compareceu',
    'remarcado',
    'cancelado'
  ));

alter table public.appointments
  alter column status set default 'agendado';
