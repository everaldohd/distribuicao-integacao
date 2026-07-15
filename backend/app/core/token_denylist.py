"""Denylist de tokens revogados (logout) — Redis com fallback em memória.

Por que existe: o JWT é stateless; sem isto, um token continua válido até o
`exp` mesmo após logout. Aqui guardamos o `jti` dos tokens revogados com TTL
igual ao tempo de vida restante do token (depois disso o próprio `exp` já o
invalida, e a chave expira sozinha no Redis).

Fallback em memória: mantém dev e a suíte de testes funcionando sem Redis.
Limitação (aceitável nesses cenários, NÃO em produção multi-réplica): a
revogação vale só para o processo atual e se perde no restart.
"""

import time

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_KEY_PREFIX = "token:denylist:"


class _MemoryDenylist:
    def __init__(self) -> None:
        self._items: dict[str, float] = {}

    def add(self, jti: str, ttl_seconds: int) -> None:
        self._purge()
        self._items[jti] = time.monotonic() + ttl_seconds

    def contains(self, jti: str) -> bool:
        self._purge()
        return jti in self._items

    def _purge(self) -> None:
        now = time.monotonic()
        self._items = {k: exp for k, exp in self._items.items() if exp > now}


class TokenDenylist:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._redis = None
        self._memory = _MemoryDenylist()
        self._use_memory = False

    def _client(self):
        """Conexão Redis preguiçosa; na 1ª falha cai para memória (com aviso)."""
        if self._use_memory:
            return None
        if self._redis is None:
            import redis

            try:
                client = redis.Redis.from_url(
                    self._redis_url,
                    socket_connect_timeout=0.5,
                    socket_timeout=0.5,
                    decode_responses=True,
                )
                client.ping()
                self._redis = client
            except Exception:
                logger.warning(
                    "Redis indisponível — denylist de tokens EM MEMÓRIA "
                    "(ok em dev/testes; em produção a revogação de logout "
                    "não sobrevive a restart nem vale entre réplicas)."
                )
                self._use_memory = True
        return self._redis

    def add(self, jti: str, ttl_seconds: int) -> None:
        ttl = max(int(ttl_seconds), 1)
        client = self._client()
        if client is not None:
            try:
                client.setex(_KEY_PREFIX + jti, ttl, "1")
                return
            except Exception:
                logger.warning("Falha ao gravar no Redis — denylist em memória.")
                self._use_memory = True
        self._memory.add(jti, ttl)

    def contains(self, jti: str) -> bool:
        client = self._client()
        if client is not None:
            try:
                return bool(client.exists(_KEY_PREFIX + jti))
            except Exception:
                logger.warning("Falha ao ler do Redis — denylist em memória.")
                self._use_memory = True
        return self._memory.contains(jti)


denylist = TokenDenylist(settings.REDIS_URL)
