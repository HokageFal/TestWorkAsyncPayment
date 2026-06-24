from httpx import AsyncClient

# Shared AsyncClient — initialized in lifespan (app/main.py), used by consumer
http_client: AsyncClient | None = None
