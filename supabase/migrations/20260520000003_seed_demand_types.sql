-- =============================================================================
-- Seed: tipos de demanda por área do direito
-- =============================================================================
-- Os IDs das áreas são UUIDs gerados em runtime; resolvemos via JOIN por nome.
-- A constraint UNIQUE (legal_area_id, name) torna a migração idempotente.
-- =============================================================================

insert into public.demand_types (legal_area_id, name)
select la.id, dt.name
from (values
  -- Direito Civil
  ('Direito Civil',           'Indenização por danos morais'),
  ('Direito Civil',           'Indenização por danos materiais'),
  ('Direito Civil',           'Cobrança'),
  ('Direito Civil',           'Revisão contratual'),
  ('Direito Civil',           'Despejo'),

  -- Direito de Família
  ('Direito de Família',      'Divórcio consensual'),
  ('Direito de Família',      'Divórcio litigioso'),
  ('Direito de Família',      'Pensão alimentícia'),
  ('Direito de Família',      'Guarda de filhos'),
  ('Direito de Família',      'Reconhecimento de paternidade'),
  ('Direito de Família',      'União estável'),

  -- Direito do Consumidor
  ('Direito do Consumidor',   'Defeito em produto'),
  ('Direito do Consumidor',   'Cobrança indevida'),
  ('Direito do Consumidor',   'Negativação indevida'),
  ('Direito do Consumidor',   'Cancelamento de serviço'),
  ('Direito do Consumidor',   'Atraso em entrega'),

  -- Direito Trabalhista
  ('Direito Trabalhista',     'Rescisão contratual'),
  ('Direito Trabalhista',     'Verbas rescisórias'),
  ('Direito Trabalhista',     'Assédio moral'),
  ('Direito Trabalhista',     'Acidente de trabalho'),
  ('Direito Trabalhista',     'Equiparação salarial'),
  ('Direito Trabalhista',     'Horas extras'),

  -- Direito Previdenciário
  ('Direito Previdenciário',  'Aposentadoria por idade'),
  ('Direito Previdenciário',  'Aposentadoria por tempo de contribuição'),
  ('Direito Previdenciário',  'Aposentadoria por invalidez'),
  ('Direito Previdenciário',  'BPC/LOAS'),
  ('Direito Previdenciário',  'Auxílio-doença'),
  ('Direito Previdenciário',  'Pensão por morte'),
  ('Direito Previdenciário',  'Revisão de benefício'),

  -- Direito Penal
  ('Direito Penal',           'Queixa-crime'),
  ('Direito Penal',           'Defesa criminal'),
  ('Direito Penal',           'Habeas corpus'),
  ('Direito Penal',           'Execução penal'),

  -- Direito Administrativo
  ('Direito Administrativo',  'Concurso público'),
  ('Direito Administrativo',  'Servidor público'),
  ('Direito Administrativo',  'Licitação'),
  ('Direito Administrativo',  'Ato administrativo'),

  -- Direito Tributário
  ('Direito Tributário',      'Restituição de imposto'),
  ('Direito Tributário',      'Parcelamento de débitos'),
  ('Direito Tributário',      'Isenção tributária'),

  -- Direito Imobiliário
  ('Direito Imobiliário',     'Usucapião'),
  ('Direito Imobiliário',     'Regularização de imóvel'),
  ('Direito Imobiliário',     'Ação possessória'),
  ('Direito Imobiliário',     'Contrato de locação'),

  -- Direito Sucessório
  ('Direito Sucessório',      'Inventário'),
  ('Direito Sucessório',      'Testamento'),
  ('Direito Sucessório',      'Partilha de bens'),
  ('Direito Sucessório',      'Arrolamento')
) as dt(area_name, name)
join public.legal_areas la on la.name = dt.area_name
on conflict (legal_area_id, name) do nothing;
