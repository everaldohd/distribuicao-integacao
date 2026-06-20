"""
Limitador de taxa (rate limit) compartilhado.

Usado para proteger endpoints sensíveis (ex.: /auth/login) contra força bruta.
A chave é o IP de origem. O limitador é registrado no app em main.py e aplicado
nos endpoints via decorator `@limiter.limit("...")`.

Observação: o armazenamento padrão é em memória (suficiente para uma única
instância). Em produção com múltiplas réplicas, configure um backend Redis.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
