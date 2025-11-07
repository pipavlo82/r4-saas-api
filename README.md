# R4 SaaS API (MVP)

Gateway для RE4CTOR core/vrf:
- `GET /v1/health`
- `GET /v1/random` → проксі на `:8080/random`
- `GET /v1/vrf?sig=ecdsa|dilithium` → проксі на `:8081/random_dual`

## Quickstart
```bash
cp .env.example .env
docker compose up -d --build
curl -s http://127.0.0.1:8082/v1/health
curl -s -H "X-API-Key: demo" "http://127.0.0.1:8082/v1/vrf?sig=ecdsa" | jq

