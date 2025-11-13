#!/usr/bin/env bash
set -euo pipefail

GATEWAY_IMAGE="pipavlo/r4-saas-api:v0.1.5"
CORE_IMAGE="r4-saas-api-r4core8080"
VRF_IMAGE="pipavlo/r4-local-test:latest"

echo "🚀 RE4CTOR SaaS — full local stack"

echo "👉 Creating docker network r4net (if missing)..."
docker network create r4net 2>/dev/null || true

echo "👉 Stopping old containers (if any)..."
docker rm -f r4-saas-api-gateway-1 r4core8080 r4-vrf 2>/dev/null || true

echo "👉 Starting dev CORE (r4core8080) from ${CORE_IMAGE}..."
docker run -d --name r4core8080 \
  --network r4net \
  "${CORE_IMAGE}"

echo "👉 Starting VRF node (r4-vrf) from ${VRF_IMAGE}..."
docker run -d --name r4-vrf \
  --network r4net \
  -e API_KEY=demo \
  "${VRF_IMAGE}"

echo "👉 Starting SaaS API Gateway on :8082 from ${GATEWAY_IMAGE}..."
docker run -d --name r4-saas-api-gateway-1 \
  --network r4net \
  -p 8082:8082 \
  -e CORE_URL="http://r4core8080:8080" \
  -e VRF_URL="http://r4-vrf:8081" \
  -e PUBLIC_API_KEY="demo" \
  -e INTERNAL_R4_API_KEY="demo" \
  "${GATEWAY_IMAGE}"

echo
echo "✅ Stack is up:"
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}' | sed -n '1p;/r4/p'

echo
echo "🔍 Quick health checks:"
echo "  curl -s  \"http://127.0.0.1:8082/v1/health\""
echo "  curl -s  \"http://127.0.0.1:8082/v1/meta\" | jq ."
echo
echo "🎲 Random via SaaS gateway:"
echo "  curl -H \"X-API-Key: demo\" \\"
echo "    \"http://127.0.0.1:8082/v1/random?n=16&fmt=hex\""
echo
echo "🔐 VRF via SaaS gateway:"
echo "  curl -s -H \"X-API-Key: demo\" \\"
echo "    \"http://127.0.0.1:8082/v1/vrf?sig=ecdsa\" | jq ."
echo
echo "🌐 Open in browser:"
echo "  http://127.0.0.1:8082/"
echo "  http://127.0.0.1:8082/docs"
