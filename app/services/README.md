# app/services

Regras de negócio reutilizáveis entre módulos e **integrações externas**:

- Cliente Supabase (Auth, Storage).
- Envio de e-mail/notificações (versões futuras).
- Gerenciamento de uploads.

Serviços muito específicos de um domínio devem ficar em `modules/<dominio>/service.py`.
