# 🧩 R4 SaaS API — Unified Gateway for RE4CTOR

> **Enterprise-grade API gateway for RE4CTOR Core + VRF services**

[![Status](https://img.shields.io/badge/status-MVP-blue?style=flat-square)](#status)
[![Python](https://img.shields.io/badge/python-3.11+-green?style=flat-square)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115+-blue?style=flat-square)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-compose-blue?style=flat-square)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green?style=flat-square)](LICENSE)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Quick Start](#-quick-start)
- [API Reference](#-api-reference)
- [Examples](#-examples)
- [Performance](#-performance)
- [Architecture](#-architecture)
- [Configuration](#-configuration)
- [Docker Compose](#-docker-compose)
- [Development](#-development)
- [Status](#-status)
- [Support](#-support)
- [License](#-license)

---

## 🧠 Overview

R4 SaaS API is a **unified HTTP gateway** that sits between clients and RE4CTOR's internal services:

- **:8080 — Core RNG** — High-entropy random number generation  
- **:8081 — VRF Node** — Verifiable randomness with `ECDSA(secp256k1) + ML-DSA-65` dual-signing

The gateway exposes a clean, public-facing API on **:8082**.

**Key Features:**

- ✅ **Single API Endpoint** — One gateway for all RE4CTOR services
- ✅ **Unified Authentication** — API key–based access for VRF/verify
- ✅ **Low Latency (MVP)** — ~30–50 ms end-to-end on dev laptop (Docker)
- ✅ **VRF + Verification** — Request randomness + verify signatures off-chain
- ✅ **Production-Ready Skeleton** — Docker Compose, env-driven config
- ✅ **Extensible** — Rate limits, metrics, billing can be added on top

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- `curl` and `jq`
- Port `8082` available on host

### Setup & Run

```bash
# Clone and enter directory
git clone https://github.com/pipavlo82/r4-saas-api.git
cd r4-saas-api

# Copy environment config
cp .env.example .env

# Build & start all services (core + vrf + gateway)
docker compose up -d --build

# Verify gateway is healthy
curl -s http://127.0.0.1:8082/v1/health
# → {"ok": true}

# Check metadata (version + upstreams)
curl -s http://127.0.0.1:8082/v1/meta | jq .
```

### First Requests

```bash
# Get random bytes (16 bytes, hex) – proxied to core (:8080)
curl -s "http://127.0.0.1:8082/v1/random?n=16&fmt=hex"
# → 32-char hex string, e.g. "9c935e210df86f0065b937f87e205bbd"

# Get random bytes as JSON
curl -s "http://127.0.0.1:8082/v1/random?n=16&fmt=json" | jq .
# → { "hex": "...", "n": 16, "source": "core-dev" }

# Get verifiable randomness (ECDSA VRF) – requires API key
curl -s -H "X-API-Key: demo" \
  "http://127.0.0.1:8082/v1/vrf?sig=ecdsa" | jq .
# → { "random": ..., "v": 27/28, "r": "0x...", "s": "0x...", ... }
```

---

## 📚 API Reference

### 1. Health Check

```http
GET /v1/health
```

Simple liveness check.

**Response:**

```json
{ "ok": true }
```

---

### 2. Meta Info

```http
GET /v1/meta
```

Returns gateway version and upstream URLs.

**Response (example):**

```json
{
  "gateway_version": "v0.1.5",
  "core_url": "http://r4core8080:8080",
  "vrf_url": "http://r4core:8081"
}
```

---

### 3. Plan & Limits

```http
GET /v1/limits
```

Static demo info about rate limits and pricing.

**Response (dev/demo):**

```json
{
  "plan": "dev",
  "rate_limit_per_min": 60,
  "price_per_call_usd": 0.001,
  "notes": "demo limits; contact sales for production tiers"
}
```

All responses also include rate-limit headers:

```http
X-R4-RateLimit-Limit: 60
X-R4-RateLimit-Remaining: 60
X-R4-Plan: dev
X-R4-Price: 0.001
```

(These are static in MVP, but wired for future real limits/billing.)

---

### 4. Random Bytes

```http
GET /v1/random?n=16&fmt=hex
```

**Query parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `n` | integer | ✅ | — | Number of bytes (1–1_000_000) |
| `fmt` | string | ❌ | `hex` | `hex` or `json` (MVP) |

**Auth:**
Currently no API key required for `/v1/random` in dev.
(Production will likely require a key.)

**Response (`fmt=hex`):**

Content-Type: `text/plain`

Body: hex string of length `2*n`

```
9c935e210df86f0065b937f87e205bbd
```

**Response (`fmt=json`):**

```json
{
  "hex": "3e4b250d25c97b83a09844bd58c9a102",
  "n": 16,
  "source": "core-dev"
}
```

---

### 5. Verifiable Randomness (VRF)

```http
GET /v1/vrf?sig=ecdsa
```

**Query parameters:**

| Name | Type | Required | Values | Description |
|------|------|----------|--------|-------------|
| `sig` | string | ✅ | `ecdsa` | Signature algorithm |

`sig=dilithium` / ML-DSA is reserved for future enterprise builds.

**Authentication:**

```http
X-API-Key: demo
```

**Response (example):**

```json
{
  "random": 3665324503,
  "timestamp": "2025-11-08T03:20:01Z",
  "hash_alg": "SHA-256",
  "signature_type": "ECDSA(secp256k1) + ML-DSA-65",
  "v": 28,
  "r": "0xedc14893d8b7c80316fcbdb9884548fde0a7d2bc4d90869c166bbe553311763a",
  "s": "0x2727deb13157d33c7218c74c6bea9365eb552d9a0a05d2de9c7ebcd0083ab362",
  "msg_hash": "0xc4f209ac3cd86f99c76abb138d91ac09206595cb6ed7ce8ece1c9cb02231e4a6",
  "signer_addr": "0x1C901e3bd997BD46a9AE3967F8632EFbDFe72293",
  "pq_scheme": "ML-DSA-65"
}
```

- `v` is 27 or 28 as in standard Ethereum signatures
- `msg_hash` is the 32-byte Keccak-256 hash that was signed
- `signer_addr` is the canonical Ethereum-style address that should be recovered from `(msg_hash, v, r, s)`

---

### 6. Signature Verification

```http
POST /v1/verify
Content-Type: application/json
```

Verifies that `(msg_hash, v, r, s)` matches the expected Ethereum address.

**Request body:**

```json
{
  "msg_hash": "c4f209ac3cd86f99c76abb138d91ac09206595cb6ed7ce8ece1c9cb02231e4a6",
  "r":       "edc14893d8b7c80316fcbdb9884548fde0a7d2bc4d90869c166bbe553311763a",
  "s":       "2727deb13157d33c7218c74c6bea9365eb552d9a0a05d2de9c7ebcd0083ab362",
  "v":       28,
  "expected_signer": "0x1C901e3bd997BD46a9AE3967F8632EFbDFe72293"
}
```

- `msg_hash`, `r`, `s`: 64 hex chars, no `0x` (gateway also accepts `0x` and normalizes)
- `v`: 0 / 1 / 27 / 28 — gateway normalizes 27/28 → 0/1 internally
- `expected_signer`: checksummed Ethereum address

**Response (valid signature & matching signer):**

```json
{
  "ok": true,
  "match": true,
  "recovered": "0x1C901e3bd997BD46a9AE3967F8632EFbDFe72293",
  "expected": "0x1C901e3bd997BD46a9AE3967F8632EFbDFe72293",
  "v_used": 1
}
```

**Response (valid sig but different signer):**

```json
{
  "ok": true,
  "match": false,
  "recovered": "0xDeadBeef00000000000000000000000000000000",
  "expected": "0x1C901e3bd997BD46a9AE3967F8632EFbDFe72293",
  "v_used": 1
}
```

**Response (bad input):**

```json
{
  "detail": "msg_hash/r/s must be 64-hex (no 0x)"
}
```

or

```json
{
  "detail": "recover_failed: BadSignature: ..."
}
```

---

## 📝 Examples

### Example 1 — Random Bytes for a Session Key

```bash
# Generate 32 random bytes (base16)
curl -s "http://127.0.0.1:8082/v1/random?n=32&fmt=json" | jq -r '.hex'
# → e.g. "3a0f1c2d4b9f5e0a6c3d4e5f1a2b3c4d..."
```

---

### Example 2 — VRF + Verify (Shell + jq)

```bash
# 1) Request VRF output
curl -s -H "X-API-Key: demo" \
  "http://127.0.0.1:8082/v1/vrf?sig=ecdsa" \
  -o /tmp/vrf.json

# 2) Build clean payload for /v1/verify
jq -n --slurpfile J /tmp/vrf.json '
  def clean: sub("^0x";"") | ascii_downcase | gsub("[^0-9a-f]";"");
  def pad64: (64 - length) as $n | if $n>0 then ("0"* $n)+. else . end;
  {
    msg_hash: ($J[0].msg_hash|tostring|clean|pad64),
    r:        ($J[0].r       |tostring|clean|pad64),
    s:        ($J[0].s       |tostring|clean|pad64),
    v:        ($J[0].v|tostring|tonumber),
    expected_signer: ($J[0].signer_addr|tostring)
  }' > /tmp/verify_req.json

# 3) Call /v1/verify
curl -sS -H "Accept: application/json" -H "Content-Type: application/json" \
     --data-binary @/tmp/verify_req.json \
     http://127.0.0.1:8082/v1/verify | jq .
```

---

### Example 3 — Python Integration

```python
import requests

API_KEY = "demo"
BASE_URL = "http://127.0.0.1:8082"

# 1) Random hex
r = requests.get(f"{BASE_URL}/v1/random?n=16&fmt=json")
r.raise_for_status()
hex_random = r.json()["hex"]
print("Random hex:", hex_random)

# 2) VRF
vrf = requests.get(
    f"{BASE_URL}/v1/vrf?sig=ecdsa",
    headers={"X-API-Key": API_KEY},
)
vrf.raise_for_status()
vrf_data = vrf.json()

# 3) Verify
verify_payload = {
    "msg_hash": vrf_data["msg_hash"].removeprefix("0x"),
    "r":        vrf_data["r"].removeprefix("0x"),
    "s":        vrf_data["s"].removeprefix("0x"),
    "v":        vrf_data["v"],
    "expected_signer": vrf_data["signer_addr"],
}
v = requests.post(f"{BASE_URL}/v1/verify", json=verify_payload)
v.raise_for_status()
print("Verify response:", v.json())
```

---

## ⚡ Performance

### Local Dev (Docker on Laptop)

Measured with sequential curl from WSL2 to Docker:

| Operation | Avg Latency | Notes |
|-----------|-------------|-------|
| `/v1/random?n=16&fmt=hex` | ~15–20 ms | Single client, sequential |
| `/v1/vrf` + `/v1/verify` | ~30–40 ms | End-to-end VRF+verify loop |

These are dev numbers (Python + Docker + localhost networking).
Production deployments on optimized Linux, with in-process core, can go down to single-digit ms.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│                 Client / dApp              │
│   (curl, backend, game server, L2 relayer) │
└───────────────────────────┬────────────────┘
                            │  HTTPS / HTTP
                            ▼
┌─────────────────────────────────────────────┐
│          R4 SaaS API Gateway (:8082)       │
│  • FastAPI / Uvicorn                       │
│  • API-key auth for VRF/verify             │
│  • CORS enabled (MVP: allow all)           │
│  • X-R4-* rate limit headers               │
└───────────────┬────────────────────────────┘
                │
      Internal HTTP (Docker network)
      ├────────────────────────────────┐
      ▼                                ▼
┌─────────────────────┐       ┌──────────────────────┐
│ RE4CTOR Core        │       │ RE4CTOR VRF Node     │
│ :8080 /random       │       │ :8081 /random_dual   │
│ Source: core-dev    │       │ ECDSA + ML-DSA-65    │
└─────────────────────┘       └──────────────────────┘
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Gateway listen port | `8082` |
| `PUBLIC_API_KEY` | Public API key (future use) | `demo` |
| `INTERNAL_R4_API_KEY` | Internal key for VRF/core calls | `demo` |
| `CORE_URL` | URL of core RNG service | `http://r4core8080:8080` |
| `VRF_URL` | URL of VRF service | `http://r4core:8081` |
| `GATEWAY_VERSION` | Version string exposed in /v1/meta | `v0.1.5` |
| `LOG_LEVEL` | Log level | `info` |

### .env Example

```bash
PORT=8082
PUBLIC_API_KEY=demo
INTERNAL_R4_API_KEY=demo

CORE_URL=http://r4core8080:8080
VRF_URL=http://r4core:8081

GATEWAY_VERSION=v0.1.5
LOG_LEVEL=info
```

---

## 🐳 Docker Compose

Minimal stack included in `docker-compose.yml`:

```yaml
services:
  # RE4CTOR Core (:8080)
  r4core8080:
    image: r4-saas-api-r4core8080
    container_name: r4core8080
    ports:
      - "8080:8080"

  # RE4CTOR VRF (:8081)
  r4core:
    image: pipavlo/r4-local-test:latest
    container_name: r4core
    environment:
      - API_KEY=demo
    ports:
      - "8081:8081"

  # R4 SaaS Gateway (:8082)
  gateway:
    image: pipavlo/r4-saas-api:v0.1.5
    container_name: r4-saas-api-gateway-1
    environment:
      - PORT=8082
      - PUBLIC_API_KEY=demo
      - CORE_URL=http://r4core8080:8080
      - VRF_URL=http://r4core:8081
      - INTERNAL_R4_API_KEY=demo
      - GATEWAY_VERSION=v0.1.5
    ports:
      - "8082:8082"
    depends_on:
      - r4core
      - r4core8080
```

---

## 🛠️ Development

### Local Dev (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt

export PORT=8082
export CORE_URL=http://127.0.0.1:8080
export VRF_URL=http://127.0.0.1:8081

uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload
```

You'll still need running instances of the core and vrf services.

---

## 📦 Status

| Component | Status | Notes |
|-----------|--------|-------|
| Gateway MVP | ✅ Done | Core + VRF + Verify wired |
| `/v1/health` | ✅ Done | Basic health |
| `/v1/meta` | ✅ Done | Version + URLs |
| `/v1/limits` | ✅ Done | Static demo info |
| `/v1/random` | ✅ Done | Hex/JSON |
| `/v1/vrf` | ✅ Done | ECDSA + PQ metadata |
| `/v1/verify` | ✅ Done | Off-chain ECDSA verification |
| CORS | ✅ Done | MVP: `*` origins |
| Rate limiting | 🟨 Plan | Real per-key limits (future) |
| Metrics / tracing | 🟨 Plan | Prometheus / OpenTelemetry |
| Enterprise build | 🟨 Plan | Multi-tenant, PQ-only, FIPS-204 |

---

## 📞 Support

- **Issues:** https://github.com/pipavlo82/r4-saas-api/issues
- **Discussions:** https://github.com/pipavlo82/r4-saas-api/discussions
- **Enterprise / PQ / FIPS-204:** shtomko@gmail.com (subject: "R4 ENTERPRISE")

---

## 📄 License

Apache License 2.0 — see [LICENSE](LICENSE).

---

<div align="center">

R4 SaaS API — unified gateway for RE4CTOR Core + VRF

[GitHub](https://github.com/pipavlo82/r4-saas-api) • [Issues](https://github.com/pipavlo82/r4-saas-api/issues) • [Discussions](https://github.com/pipavlo82/r4-saas-api/discussions)

</div>
