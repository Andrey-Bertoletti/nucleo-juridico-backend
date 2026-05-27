-- =============================================================================
-- Templates: descrição curta + segurança no delete físico
-- =============================================================================
-- - Adiciona `description` para o admin documentar pra que serve o modelo
--   (vai aparecer na lista, não no documento gerado).
-- - O conteúdo (`content`) passa a ser HTML enriquecido (vindo do editor
--   Tiptap no frontend). Não há mudança de tipo de coluna — `text` continua
--   suficiente — mas vale notar pra leitores futuros.
-- =============================================================================

alter table public.templates
  add column if not exists description varchar(500);
