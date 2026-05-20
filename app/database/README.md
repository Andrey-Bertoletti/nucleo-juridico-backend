# app/database

Camada de persistência:

- `session.py` — engine e `SessionLocal` do SQLAlchemy, dependência `get_db`.
- `base.py` — `Base = declarative_base()` central; agrega os modelos para o Alembic.
- `models/` — modelos ORM globais (ou definidos dentro de cada módulo, à escolha do time).
- `migrations/` — diretório do Alembic com as migrações versionadas.

O banco é PostgreSQL gerenciado pelo Supabase; o cliente HTTP do Supabase (Storage/Auth) fica em `services/`.
