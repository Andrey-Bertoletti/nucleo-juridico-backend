"""Rate limit in-memory simples — mitiga brute-force em endpoints de auth.

Limitações conhecidas:
  * Estado em memória do processo — em deploys com múltiplos workers, cada
    worker tem sua própria janela. Bom para single-worker free tier; em
    produção real, trocar por Redis/Memcached/limite na borda (Cloudflare,
    Render rate limit, etc.).
  * Não há clean-up automático além do lazy: chaves antigas são removidas
    quando a janela expira e a chave é consultada de novo.

Estratégia:
  * Janela deslizante por chave (IP_remoto + email-em-minusculas).
  * Quando o número de tentativas dentro de `window_seconds` ultrapassa
    `max_attempts`, levanta HTTP 429 e devolve `Retry-After` em segundos.
  * `reset()` é chamado em login bem-sucedido para limpar o histórico
    daquela chave (evita punir um usuário que digitou a senha errada uma
    ou duas vezes antes de acertar).
"""

from __future__ import annotations

import time
from collections import deque
from threading import Lock

from fastapi import HTTPException, Request, status


class _SlidingWindowLimiter:
    def __init__(self, *, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def hit(self, key: str) -> tuple[bool, int]:
        """Registra uma tentativa. Retorna (permitido, retry_after_seconds)."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            queue = self._hits.setdefault(key, deque())
            while queue and queue[0] < cutoff:
                queue.popleft()
            if len(queue) >= self.max_attempts:
                retry_after = max(1, int(self.window_seconds - (now - queue[0])))
                return False, retry_after
            queue.append(now)
            return True, 0

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)


# 5 tentativas em 60 s por (IP, email). Suficiente para uso humano e
# desestimula scripts.
login_limiter = _SlidingWindowLimiter(max_attempts=5, window_seconds=60)


def _client_ip(request: Request) -> str:
    """Resolve o IP confiando em X-Forwarded-For atrás do proxy do Render.

    A FastAPI/uvicorn precisa ter sido iniciada com `--proxy-headers
    --forwarded-allow-ips=*` (já é o startCommand do `render.yaml`).
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # X-Forwarded-For pode ter cadeia "client, proxy1, proxy2".
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host or "anonymous"
    return "anonymous"


def enforce_login_rate_limit(request: Request, email: str) -> str:
    """Aplica o rate limit; em caso de bloqueio, levanta 429."""
    key = f"{_client_ip(request)}|{email.lower().strip()}"
    allowed, retry_after = login_limiter.hit(key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Aguarde antes de tentar novamente.",
            headers={"Retry-After": str(retry_after)},
        )
    return key


def reset_login_rate_limit(key: str) -> None:
    login_limiter.reset(key)
