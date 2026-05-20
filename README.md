# nucleo-juridico-backend

Backend (API REST) do **Sistema de Gestão de Atendimento Jurídico** — responsável por expor os recursos de atendimento, clientes/assistidos, triagem, documentos, orientação de professores e acompanhamento de casos.

---

## Stack

- **Python 3.11+**
- **FastAPI** (framework web)
- **Uvicorn** (ASGI server)
- **SQLAlchemy** + **Alembic** (ORM e migrações)
- **Pydantic v2** (validação e schemas)
- **PostgreSQL** gerenciado pelo **Supabase**
- **Supabase Storage** para documentos
- Autenticação via **Supabase Auth** (validação de JWT)

---

## Estrutura de pastas

```
nucleo-juridico-backend/
├── app/
│   ├── main.py         # Entrada da aplicação FastAPI
│   ├── core/           # Configuração, settings, segurança, dependências globais
│   ├── modules/        # Módulos de domínio (rotas + lógica por feature)
│   ├── database/       # Sessão do banco, modelos ORM, migrações
│   ├── schemas/        # Schemas Pydantic (request/response)
│   ├── services/       # Regras de negócio reutilizáveis e integrações externas
│   └── utils/          # Funções utilitárias genéricas
├── .env.example
├── .gitignore
├── PROJECT_SCOPE.md
├── requirements.txt
└── README.md
```

### Convenções por pasta

| Pasta         | Responsabilidade                                                                 |
|---------------|----------------------------------------------------------------------------------|
| `main.py`     | Cria a instância FastAPI, registra middlewares e inclui os routers de `modules/`. |
| `core/`       | `settings` (env vars), `security` (JWT/Supabase), dependências de injeção comuns. |
| `modules/`    | Cada subpasta = um domínio (`atendimento`, `clientes`, `casos`...) com `router.py`, `service.py`, etc. |
| `database/`   | `session.py`, `base.py`, modelos SQLAlchemy e diretório de migrações Alembic.    |
| `schemas/`    | Schemas Pydantic globais. Schemas específicos podem viver dentro do módulo.       |
| `services/`   | Lógica de negócio compartilhada entre módulos e integrações (Supabase Storage, e-mail, etc.). |
| `utils/`      | Helpers puros (formatadores, parsers, validações genéricas).                      |

---

## Como rodar (após o setup do projeto)

```bash
# 1) criar e ativar venv (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) instalar dependências
pip install -r requirements.txt

# 3) copiar variáveis de ambiente
copy .env.example .env
# edite o .env com as credenciais reais

# 4) rodar em modo desenvolvimento
uvicorn app.main:app --reload
```

A API ficará disponível em `http://localhost:8000`. A documentação interativa em `http://localhost:8000/docs`.

---

## Documentação relacionada

- [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) — escopo, perfis de usuário e funcionalidades planejadas.
- Repositório do frontend: `nucleo-juridico-frontend`.
