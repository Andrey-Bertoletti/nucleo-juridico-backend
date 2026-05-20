# app/modules

Módulos por **domínio do sistema**. Cada subpasta representa um domínio (`atendimento`, `clientes`, `triagem`, `casos`, `documentos`, `usuarios`...) e deve conter, no mínimo:

```
modules/<dominio>/
├── __init__.py
├── router.py     # endpoints FastAPI (APIRouter)
├── service.py    # regras de negócio do domínio
├── models.py     # modelos SQLAlchemy (se específicos)
└── schemas.py    # schemas Pydantic do domínio
```

Cada `router.py` exporta um `router: APIRouter` que será incluído em `app/main.py`.
