"""
Bootstrap de usuários para ambientes de desenvolvimento.

Cria duas contas no Supabase Auth + os profiles correspondentes:

  - admin@ites.edu.br     / Admin@1234       — admin_coordenacao
  - professor@ites.edu.br / Professor@1234   — professor_orientador

Pré-requisitos:
  1. `.env` configurado (DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY...).
  2. Migrações aplicadas no banco (`supabase db push` ou equivalente).
  3. Dependências instaladas (`pip install -r requirements.txt`).

Execução (a partir da raiz do projeto backend):

    python scripts/seed_users.py

O script é idempotente: usuários já existentes (mesmo e-mail) são pulados.
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

# Permite executar como `python scripts/seed_users.py` a partir da raiz do
# projeto (mesmo sem instalar o pacote).
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.session import SessionLocal  # noqa: E402
from app.modules.users.models import Profile  # noqa: E402
from app.services.supabase_client import get_admin_client  # noqa: E402


SEED_USERS: list[dict[str, str]] = [
    {
        "name": "Coordenação NPJ",
        "email": "admin@ites.com.br",
        "password": "Admin@1234",
        "role": "admin_coordenacao",
    },
    {
        "name": "Professor Exemplo",
        "email": "professor@ites.edu.br",
        "password": "Professor@1234",
        "role": "professor_orientador",
    },
]


def ensure_user(db, admin_client, user: dict[str, str]) -> None:
    email = user["email"]
    existing = db.query(Profile).filter(Profile.email == email).first()
    if existing is not None:
        print(f"[skip ] {email} já existe (role={existing.role}).")
        return

    try:
        result = admin_client.auth.admin.create_user(
            {
                "email": email,
                "password": user["password"],
                "email_confirm": True,
                "user_metadata": {
                    "name": user["name"],
                    "role": user["role"],
                },
            }
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[error] falha ao criar {email} no Supabase Auth: {exc}")
        return

    auth_user = getattr(result, "user", None)
    if auth_user is None or getattr(auth_user, "id", None) is None:
        print(f"[error] resposta inválida do Supabase para {email}.")
        return

    profile = Profile(
        user_id=UUID(str(auth_user.id)),
        name=user["name"],
        email=email,
        role=user["role"],
        status="ativo",
    )
    db.add(profile)
    db.commit()
    print(f"[ok   ] criado {email}  (role={user['role']})")


def main() -> None:
    db = SessionLocal()
    admin = get_admin_client()
    try:
        for user in SEED_USERS:
            ensure_user(db, admin, user)
    finally:
        db.close()

    print()
    print("Credenciais criadas para uso em desenvolvimento:")
    print("  admin@ites.com.br     / Admin@1234       (admin_coordenacao)")
    print("  professor@ites.edu.br / Professor@1234   (professor_orientador)")
    print()
    print("Troque as senhas antes de qualquer uso em produção.")


if __name__ == "__main__":
    main()
