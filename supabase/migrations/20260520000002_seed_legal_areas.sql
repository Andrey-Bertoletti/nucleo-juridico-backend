-- =============================================================================
-- Seed: áreas do direito
-- =============================================================================
-- Carrega a taxonomia inicial de áreas do direito.
-- `on conflict (name) do nothing` torna a migração idempotente.
-- =============================================================================

insert into public.legal_areas (name) values
  ('Direito Civil'),
  ('Direito de Família'),
  ('Direito do Consumidor'),
  ('Direito Trabalhista'),
  ('Direito Previdenciário'),
  ('Direito Penal'),
  ('Direito Administrativo'),
  ('Direito Tributário'),
  ('Direito Imobiliário'),
  ('Direito Sucessório')
on conflict (name) do nothing;
