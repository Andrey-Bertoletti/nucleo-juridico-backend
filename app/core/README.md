# app/core

Configuração transversal da aplicação:

- `settings.py` — leitura de variáveis de ambiente (pydantic-settings).
- `security.py` — validação de JWT do Supabase e dependências de autenticação.
- `dependencies.py` — dependências reutilizáveis injetáveis em rotas (usuário atual, sessão, etc.).

Não deve depender de módulos de domínio (`modules/`).
