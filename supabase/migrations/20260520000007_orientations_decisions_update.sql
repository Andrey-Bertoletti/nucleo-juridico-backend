-- =============================================================================
-- Orientações: atualiza vocabulário do campo `decision`
-- =============================================================================
-- Substitui o check antigo (aprovar/revisar/encaminhar/arquivar/aguardar_documentos)
-- pelas 4 decisões do fluxo do professor.
-- =============================================================================

alter table public.orientations
  drop constraint if exists orientations_decision_check;

update public.orientations
   set decision = case decision
     when 'aprovar'              then 'aprovar_encaminhamento'
     when 'revisar'              then 'solicitar_correcao'
     when 'encaminhar'           then 'aprovar_encaminhamento'
     when 'arquivar'             then 'finalizar_atendimento'
     when 'aguardar_documentos'  then 'solicitar_documentos'
     else decision
   end
 where decision is not null;

alter table public.orientations
  add constraint orientations_decision_check
  check (
    decision is null
    or decision in (
      'solicitar_correcao',
      'solicitar_documentos',
      'aprovar_encaminhamento',
      'finalizar_atendimento'
    )
  );
