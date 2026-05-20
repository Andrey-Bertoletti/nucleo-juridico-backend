# supabase/

Configurações do projeto Supabase: migrações SQL e seeds executados via [Supabase CLI](https://supabase.com/docs/guides/cli).

## Estrutura

```
supabase/
└── migrations/
    ├── 20260520000001_initial_schema.sql     # schema completo (tabelas, FKs, índices, triggers)
    ├── 20260520000002_seed_legal_areas.sql   # taxonomia: áreas do direito
    └── 20260520000003_seed_demand_types.sql  # taxonomia: tipos de demanda por área
```

## Aplicar as migrações

### Em projeto Supabase remoto
```bash
# autenticar uma vez
supabase login

# vincular ao projeto remoto
supabase link --project-ref <SEU_PROJECT_REF>

# aplicar migrações
supabase db push
```

### Em ambiente local (Supabase em Docker)
```bash
supabase start
supabase db reset      # recria o banco e roda todas as migrações
```

## Convenções

- Status, papéis e enums em **português** (`ativo`, `aberto`, `em_triagem`...).
- Todos os `id` são `uuid` com `gen_random_uuid()` (extensão `pgcrypto`).
- `created_at` e `updated_at` são `timestamptz` com `default now()`.
- `updated_at` é atualizado automaticamente por trigger (`public.set_updated_at`).
- Datas/horas sempre em `timestamptz` (UTC); o frontend formata para o fuso local.
- RLS (Row Level Security) **não** foi configurada nesta etapa — habilitar antes de expor o banco a clientes via API anônima do Supabase.
