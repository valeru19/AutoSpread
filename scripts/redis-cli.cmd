@echo off
REM Local redis-cli against Docker Redis (autospread-redis on localhost:6379)
docker compose -f "%~dp0..\docker-compose.yml" exec -T redis redis-cli %*
