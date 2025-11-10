from fastapi.responses import HTMLResponse
from app.verify_route import router as verify_router
import os, time, asyncio
from typing import Dict, Tuple
from fastapi import FastAPI, Query, Header, HTTPException, Response, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="R4 SaaS API", version=os.getenv("GATEWAY_VERSION","v0.1.3"))
app.include_router(verify_router)

PORT = int(os.getenv("PORT", "8082"))
PUBLIC_API_KEY = os.getenv("PUBLIC_API_KEY", "demo")
CORE_URL = os.getenv("CORE_URL", "http://r4core:8080")
VRF_URL = os.getenv("VRF_URL", "http://r4core:8081")
INTERNAL_R4_API_KEY = os.getenv("INTERNAL_R4_API_KEY", PUBLIC_API_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BUCKET: Dict[Tuple[str,str], Tuple[int,float]] = {}
LOCK = asyncio.Lock()
LIMITS = {"default": (60, 60.0), "vrf": (30, 60.0)}

async def check_rate(request: Request, scope: str):
    ip = request.client.host if request.client else "unknown"
    key = (ip, scope)
    tokens, window = LIMITS[scope]
    now = time.time()
    async with LOCK:
        cur_tokens, reset_ts = BUCKET.get(key, (tokens, now + window))
        if now >= reset_ts:
            cur_tokens, reset_ts = tokens, now + window
        if cur_tokens <= 0:
            retry = max(1, int(reset_ts - now))
            raise HTTPException(status_code=429, detail=f"rate limit exceeded; retry in ~{retry}s")
        BUCKET[key] = (cur_tokens - 1, reset_ts)

# ✅ ПРАВИЛЬНІ залежності для FastAPI
async def rl_default(request: Request):
    await check_rate(request, "default")

async def rl_vrf(request: Request):
    await check_rate(request, "vrf")

@app.get("/", response_class=HTMLResponse)
async def landing():
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>RE4CTOR SaaS API Gateway</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      padding: 0;
      background: #050816;
      color: #f5f5f5;
    }
    .wrap {
      max-width: 960px;
      margin: 0 auto;
      padding: 32px 16px 64px;
    }
    h1 {
      font-size: 2.2rem;
      margin-bottom: 0.5rem;
    }
    h2 {
      margin-top: 2.5rem;
      margin-bottom: 0.8rem;
      font-size: 1.4rem;
    }
    p {
      line-height: 1.5;
      color: #d1d5db;
    }
    code {
      background: #111827;
      padding: 2px 4px;
      border-radius: 4px;
      font-size: 0.9rem;
    }
    pre {
      background: #020617;
      padding: 12px 14px;
      border-radius: 8px;
      overflow-x: auto;
      font-size: 0.9rem;
      border: 1px solid #1f2937;
    }
    .pill {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.75rem;
      background: #111827;
      border: 1px solid #1d4ed8;
      color: #bfdbfe;
      margin-bottom: 0.6rem;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-top: 12px;
    }
    .card {
      background: #020617;
      border-radius: 10px;
      padding: 14px 16px;
      border: 1px solid #111827;
    }
    .badge-ok {
      display: inline-block;
      font-size: 0.75rem;
      padding: 2px 8px;
      border-radius: 999px;
      background: #022c22;
      color: #6ee7b7;
      border: 1px solid #065f46;
      margin-left: 4px;
    }
    a {
      color: #60a5fa;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    .footer {
      margin-top: 40px;
      font-size: 0.8rem;
      color: #6b7280;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <span class="pill">RE4CTOR • SaaS API Gateway</span>
    <h1>Unified gateway for RE4CTOR Core + VRF</h1>
    <p>
      Public HTTP API on top of RE4CTOR Core (:8080) and VRF node (:8081).
      Single entrypoint for random bytes, verifiable randomness and signature verification.
    </p>

    <h2>Health & metadata</h2>
    <pre><code>GET /v1/health
GET /v1/meta</code></pre>
    <pre><code>curl -s http://127.0.0.1:8082/v1/health
curl -s http://127.0.0.1:8082/v1/meta | jq .</code></pre>

    <h2>Random bytes</h2>
    <div class="card">
      <p><code>GET /v1/random?n=16&amp;fmt=hex</code> <span class="badge-ok">auth: X-API-Key</span></p>
      <p>Parameters:</p>
      <ul>
        <li><code>n</code>: number of bytes (1–1 000 000)</li>
        <li><code>fmt</code>: <code>hex</code> | <code>base64</code> | <code>raw</code></li>
      </ul>
    </div>
    <pre><code>curl -s -H "X-API-Key: demo" \
  "http://127.0.0.1:8082/v1/random?n=16&amp;fmt=hex"</code></pre>

    <h2>Verifiable randomness (VRF)</h2>
    <div class="card">
      <p><code>GET /v1/vrf?sig=ecdsa</code> <span class="badge-ok">auth: X-API-Key</span></p>
      <p>Returns random value + ECDSA(secp256k1) signature and msg_hash.</p>
    </div>
    <pre><code>curl -s -H "X-API-Key: demo" \
  "http://127.0.0.1:8082/v1/vrf?sig=ecdsa" | jq .</code></pre>

    <h2>Signature verification</h2>
    <div class="card">
      <p><code>POST /v1/verify</code> — recover signer from (msg_hash, v, r, s) and compare with expected address.</p>
    </div>
    <pre><code>curl -s -H "Content-Type: application/json" \
  -d '{"msg_hash":"...","r":"...","s":"...","v":27,"expected_signer":"0x..."}' \
  http://127.0.0.1:8082/v1/verify | jq .</code></pre>

    <h2>Developer tooling</h2>
    <div class="grid">
      <div class="card">
        <strong>OpenAPI / Swagger</strong>
        <p><code>/docs</code> &amp; <code>/openapi.json</code> exposed by FastAPI.</p>
      </div>
      <div class="card">
        <strong>Rate-limit headers</strong>
        <p><code>X-R4-RateLimit-Limit</code>, <code>X-R4-RateLimit-Remaining</code>, <code>X-R4-Plan</code>, <code>X-R4-Price</code></p>
      </div>
      <div class="card">
        <strong>CORS</strong>
        <p>Demonstration build allows <code>origin: *</code> for quick prototyping.</p>
      </div>
    </div>

    <div class="footer">
      <p>Check README for full documentation and examples. This is an MVP build used for local and staging environments.</p>
    </div>
  </div>
</body>
</html>
    """

@app.get("/v1/health")
async def health():
    return {"ok": True}

@app.get("/v1/meta")
async def meta():
    return {
        "gateway_version": app.version,
        "core_url": CORE_URL,
        "vrf_url": VRF_URL,
    }

@app.get("/v1/random")
async def random(
    request: Request,
    n: int = Query(32, ge=1, le=4096),
    fmt: str = Query("hex"),
    _=Depends(rl_default),
):
    want_json = (fmt.lower() == "json")
    core_fmt = "hex"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{CORE_URL}/random",
                params={"n": n, "fmt": core_fmt},
                headers={"X-API-Key": INTERNAL_R4_API_KEY},
            )
        if r.status_code == 200:
            hex_str = r.text.strip()
            if want_json:
                return {"hex": hex_str, "n": n, "source": "core-dev"}
            return Response(content=hex_str, media_type="text/plain", status_code=200)
        else:
            raise RuntimeError(f"core returned {r.status_code}")
    except Exception:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                rr = await client.get(
                    f"{VRF_URL}/random_dual",
                    params={"sig": "ecdsa"},
                    headers={"X-API-Key": INTERNAL_R4_API_KEY},
                )
            if rr.status_code == 200:
                j = rr.json()
                seed = int(j.get("random", 0)) & 0xFFFFFFFF
                hex4 = seed.to_bytes(4, "big").hex()
                if want_json:
                    return {"random": seed, "hex": hex4, "source": "vrf_fallback"}
                return Response(content=hex4, media_type="text/plain", status_code=200)
        except Exception:
            pass
        return Response(
            content="core (:8080) is unavailable. VRF fallback can supply only 4 bytes; please enable core for longer outputs.",
            media_type="text/plain",
            status_code=503,
        )

@app.get("/v1/vrf")
async def vrf(
    request: Request,
    sig: str = Query("ecdsa"),
    x_api_key: str = Header(default=""),
    _=Depends(rl_vrf),
):
    if x_api_key != PUBLIC_API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{VRF_URL}/random_dual",
            params={"sig": sig},
            headers={"X-API-Key": INTERNAL_R4_API_KEY},
        )
    return Response(content=r.content,
                    status_code=r.status_code,
                    media_type=r.headers.get("content-type", "application/json"))
