import os
import binascii
from typing import Optional

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Depends,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
import httpx

from eth_keys import keys
from eth_account import Account


# -------------------------------------------------------------------
# Config from environment
# -------------------------------------------------------------------

CORE_URL = os.getenv("CORE_URL", "http://r4core8080:8080")
VRF_URL = os.getenv("VRF_URL", "http://r4core:8081")
PUBLIC_API_KEY = os.getenv("PUBLIC_API_KEY", "demo")
INTERNAL_R4_API_KEY = os.getenv("INTERNAL_R4_API_KEY", "demo")
GATEWAY_VERSION = os.getenv("GATEWAY_VERSION", "v0.1.5")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")


# -------------------------------------------------------------------
# FastAPI app
# -------------------------------------------------------------------

app = FastAPI(
    title="RE4CTOR SaaS API Gateway",
    version=GATEWAY_VERSION,
)

# CORS – на всяк випадок, щоб фронт з іншого домену міг стукатись
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# Middleware: service headers
# -------------------------------------------------------------------

@app.middleware("http")
async def add_svc_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-R4-Gateway-Version"] = GATEWAY_VERSION
    resp.headers["X-R4-Core-URL"] = CORE_URL
    resp.headers["X-R4-VRF-URL"] = VRF_URL
    return resp


# -------------------------------------------------------------------
# Simple API-key auth
# -------------------------------------------------------------------

async def require_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    # або з заголовка, або з query ?api_key=
    query_key = request.query_params.get("api_key")
    api_key = x_api_key or query_key

    if api_key != PUBLIC_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return api_key


# -------------------------------------------------------------------
# Models
# -------------------------------------------------------------------

class VerifyRequest(BaseModel):
    msg_hash: str
    r: str
    s: str
    v: int
    expected_signer: str


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

HEX_CHARS = set("0123456789abcdef")


def _clean_hex_64(s: str, field: str) -> str:
    """normalize 0x, lowercase, ensure exactly 64 hex chars"""
    if s is None:
        raise HTTPException(status_code=400, detail=f"{field} is required")

    raw = s.strip().lower()
    if raw.startswith("0x"):
        raw = raw[2:]

    if len(raw) != 64 or any(c not in HEX_CHARS for c in raw):
        raise HTTPException(
            status_code=400,
            detail="msg_hash/r/s must be 64-hex (no 0x)",
        )
    return raw


def _normalize_v(v: int) -> int:
    if v in (27, 28):
        return v - 27
    if v in (0, 1):
        return v
    raise HTTPException(
        status_code=400,
        detail="v must be 0/1 or 27/28",
    )


def _normalize_address(addr: str) -> str:
    if not addr:
        return ""
    a = addr.strip()
    if not a.startswith("0x"):
        a = "0x" + a
    return a.lower()


# -------------------------------------------------------------------
# HTML landing page
# -------------------------------------------------------------------

HOMEPAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>RE4CTOR SaaS API Gateway</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {
      --bg: #020817;
      --card: #020617;
      --card2: #020c1f;
      --accent1: #22c55e;
      --accent2: #06b6d4;
      --accent-soft: rgba(34,197,94,0.15);
      --text: #e5e7eb;
      --muted: #9ca3af;
      --border: #1f2937;
      --font: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * {
      box-sizing: border-box;
    }
    body {
      margin: 0;
      padding: 0;
      font-family: var(--font);
      background: radial-gradient(circle at top, #0b1220 0%, #020617 55%, #020617 100%);
      color: var(--text);
    }
    a {
      color: inherit;
      text-decoration: none;
    }
    .page {
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 16px 64px;
    }
    .chip-row {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(15,23,42,0.9);
      border: 1px solid rgba(148,163,184,0.3);
      font-size: 12px;
      margin-bottom: 18px;
    }
    .chip-pill {
      padding: 2px 8px;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--accent1), var(--accent2));
      color: #020617;
      font-weight: 600;
    }
    .chip-sub {
      color: var(--muted);
    }
    h1 {
      font-size: 34px;
      line-height: 1.1;
      margin: 0 0 12px;
    }
    .hero-sub {
      max-width: 580px;
      color: var(--muted);
      font-size: 15px;
      line-height: 1.5;
      margin-bottom: 20px;
    }
    .hero-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 28px;
    }
    .btn-primary {
      border: none;
      outline: none;
      padding: 10px 20px;
      border-radius: 999px;
      font-weight: 600;
      font-size: 14px;
      cursor: pointer;
      background: linear-gradient(90deg, var(--accent1), var(--accent2));
      color: #020617;
      box-shadow: 0 10px 30px rgba(34,197,94,0.25);
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .btn-ghost {
      padding: 9px 18px;
      border-radius: 999px;
      border: 1px solid rgba(148,163,184,0.5);
      background: transparent;
      color: var(--text);
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
    }
    .layout-main {
      display: grid;
      grid-template-columns: minmax(0, 3fr) minmax(0, 2.4fr);
      gap: 24px;
      align-items: flex-start;
    }
    @media (max-width: 900px) {
      .layout-main {
        grid-template-columns: minmax(0,1fr);
      }
    }

    /* Snapshot */
    .snapshot-card {
      background: radial-gradient(circle at top left, #0f172a, #020617);
      border-radius: 18px;
      padding: 16px 16px 18px;
      border: 1px solid rgba(148,163,184,0.35);
      box-shadow: 0 18px 40px rgba(15,23,42,0.7);
    }
    .snapshot-header {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 4px;
    }
    .snapshot-sub {
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 10px;
    }
    .snapshot-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 12px;
    }
    .tag-pill {
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 999px;
      border: 1px solid rgba(148,163,184,0.5);
      color: var(--muted);
    }
    .tag-pill--accent {
      border: none;
      background: rgba(34,197,94,0.1);
      color: var(--accent1);
    }
    .snapshot-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 8px;
    }
    .snapshot-box {
      border-radius: 14px;
      padding: 10px;
      background: rgba(15,23,42,0.9);
      border: 1px solid rgba(31,41,55,1);
    }
    .snapshot-label {
      font-size: 11px;
      color: var(--muted);
      margin-bottom: 4px;
    }
    .snapshot-value {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 2px;
    }
    .snapshot-meta {
      font-size: 11px;
      color: var(--muted);
    }

    /* Playground */
    .section-title {
      font-size: 16px;
      font-weight: 600;
      margin: 22px 0 6px;
    }
    .section-sub {
      font-size: 13px;
      color: var(--muted);
      max-width: 640px;
      margin-bottom: 10px;
    }
    .playground-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 12px;
    }
    .playground-input {
      flex: 1 1 220px;
      min-width: 0;
      padding: 8px 10px;
      border-radius: 999px;
      border: 1px solid rgba(31,41,55,1);
      background: rgba(15,23,42,0.85);
      color: var(--text);
      font-size: 13px;
    }
    .playground-input::placeholder {
      color: rgba(148,163,184,0.7);
    }
    .playground-btn {
      border-radius: 999px;
      padding: 8px 16px;
      border: none;
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      background: linear-gradient(90deg, var(--accent1), var(--accent2));
      color: #020617;
      white-space: nowrap;
    }
    .playground-btn.secondary {
      background: rgba(15,23,42,0.95);
      border: 1px solid rgba(148,163,184,0.6);
      color: var(--text);
    }
    .log-box {
      margin-top: 10px;
      border-radius: 12px;
      background: rgba(15,23,42,0.96);
      border: 1px solid rgba(31,41,55,1);
      padding: 8px;
      font-family: "SF Mono", ui-monospace, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: 11px;
      color: #e5e7eb;
      max-height: 210px;
      overflow: auto;
      white-space: pre;
    }
    .log-line-ok {
      color: #22c55e;
    }
    .log-line-err {
      color: #f97373;
    }

    /* Curl example */
    .curl-card {
      background: rgba(15,23,42,0.98);
      border: 1px solid rgba(31,41,55,1);
      border-radius: 18px;
      padding: 14px 14px 16px;
      box-shadow: 0 18px 30px rgba(15,23,42,0.9);
      font-family: "SF Mono", ui-monospace, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: 11px;
      color: #e5e7eb;
    }
    .curl-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
      font-size: 11px;
      color: var(--muted);
    }
    .curl-badge {
      padding: 3px 8px;
      border-radius: 999px;
      border: 1px solid rgba(148,163,184,0.7);
    }
    .curl-pre {
      white-space: pre;
      overflow-x: auto;
    }
    .muted {
      color: var(--muted);
    }
  </style>
</head>
<body>
  <div class="page">
    <div class="chip-row">
      <span class="chip-pill">RE4CTOR Gateway</span>
      <span class="chip-sub">30–50ms dev latency • 600× faster than on-chain oracles</span>
    </div>

    <h1>FIPS-ready randomness API with verifiable proofs.</h1>
    <p class="hero-sub">
      RE4CTOR SaaS API is a hardened HTTP gateway in front of RE4CTOR Core RNG
      and dual-signature VRF. One endpoint for crypto, gaming, and defense workloads.
    </p>

    <div class="hero-actions">
      <button id="btn-try-api" class="btn-primary">Try live API</button>
      <button id="btn-open-docs" class="btn-ghost">Open Swagger /docs</button>
    </div>

    <div class="layout-main">
      <div>
        <div class="section-title">Live API playground</div>
        <p class="section-sub">
          Use this gateway directly from your browser. Calls go to
          <span class="muted" id="runtime-base-label">your gateway</span> and show live responses.
        </p>

        <div class="playground-row">
          <input
            id="base-url-input"
            type="text"
            class="playground-input"
            value=""
            placeholder="https://r4-saas-api.onrender.com"
          />
          <input
            id="api-key-input"
            type="text"
            class="playground-input"
            style="max-width: 200px"
            value="demo"
            placeholder="API key (X-API-Key)"
          />
        </div>

        <div class="playground-row">
          <button id="btn-call-random" class="playground-btn">Call /v1/random</button>
          <button id="btn-call-vrf" class="playground-btn secondary">Call /v1/vrf?sig=ecdsa</button>
        </div>

        <div id="log-box" class="log-box">
Ready. Click “Call /v1/random” or “Call /v1/vrf?sig=ecdsa”.
        </div>
      </div>

      <div>
        <div class="snapshot-card">
          <div class="snapshot-header">Runtime snapshot</div>
          <div class="snapshot-sub">
            Live view into your RE4CTOR SaaS gateway.
          </div>

          <div class="snapshot-tags">
            <div class="tag-pill tag-pill--accent">FIPS 204-ready 🔐</div>
            <div class="tag-pill">Post-quantum combo (ML-DSA-65)</div>
            <div class="tag-pill">On-chain proof friendly</div>
          </div>

          <div class="snapshot-grid">
            <div class="snapshot-box">
              <div class="snapshot-label">Latency (dev)</div>
              <div id="latency-value" class="snapshot-value">—</div>
              <div class="snapshot-meta">Gateway → Core</div>
            </div>
            <div class="snapshot-box">
              <div class="snapshot-label">VRF</div>
              <div class="snapshot-value">ECDSA + ML-DSA-65</div>
              <div class="snapshot-meta">Dual-signed</div>
            </div>
            <div class="snapshot-box">
              <div class="snapshot-label">Plan</div>
              <div class="snapshot-value">dev</div>
              <div class="snapshot-meta">X-R4-* headers</div>
            </div>
          </div>
        </div>

        <div style="height: 14px"></div>

        <div class="curl-card">
          <div class="curl-header">
            <span>curl example</span>
            <span class="curl-badge">copy-paste into terminal</span>
          </div>
          <div class="curl-pre">
curl -s -H "X-API-Key: demo" \\
  "<span id="curl-base-url-1">http://localhost:8082</span>/v1/random?n=16&fmt=hex"

curl -s -H "X-API-Key: demo" \\
  "<span id="curl-base-url-2">http://localhost:8082</span>/v1/vrf?sig=ecdsa" | jq .
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    (function() {
      function byId(id) { return document.getElementById(id); }
      var baseInput = byId("base-url-input");
      var apiKeyInput = byId("api-key-input");
      var logBox = byId("log-box");
      var latencyValue = byId("latency-value");
      var runtimeLabel = byId("runtime-base-label");
      var curlBase1 = byId("curl-base-url-1");
      var curlBase2 = byId("curl-base-url-2");

      var origin = window.location.origin || "";
      if (baseInput && !baseInput.value) baseInput.value = origin;
      if (runtimeLabel) runtimeLabel.textContent = origin || "your gateway";
      if (curlBase1) curlBase1.textContent = origin;
      if (curlBase2) curlBase2.textContent = origin;

      function appendLog(line, cls) {
        if (!logBox) return;
        var span = document.createElement("span");
        if (cls) span.className = cls;
        span.textContent = line + "\\n";
        logBox.appendChild(span);
        logBox.scrollTop = logBox.scrollHeight;
      }

      async function callEndpoint(path) {
        var base = (baseInput && baseInput.value.trim()) || origin;
        var key = (apiKeyInput && apiKeyInput.value.trim()) || "demo";
        if (!base) {
          appendLog("ERROR: base URL is empty", "log-line-err");
          return;
        }
        if (!base.startsWith("http")) {
          base = "https://" + base;
        }
        var url = base.replace(/\\/$/, "") + path;

        var t0 = performance.now();
        appendLog("→ GET " + url, "muted");
        try {
          var res = await fetch(url, {
            method: "GET",
            headers: { "X-API-Key": key }
          });
          var dt = Math.round(performance.now() - t0);
          if (latencyValue) latencyValue.textContent = dt + " ms";

          var text = await res.text();
          if (res.ok) {
            appendLog("← " + res.status + " OK (" + dt + " ms)", "log-line-ok");
            appendLog(text, "muted");
          } else {
            appendLog("← " + res.status + " ERROR (" + dt + " ms)", "log-line-err");
            appendLog(text, "log-line-err");
          }
        } catch (e) {
          appendLog("ERROR: " + (e && e.message ? e.message : e), "log-line-err");
        }
      }

      var btnRandom = byId("btn-call-random");
      var btnVrf = byId("btn-call-vrf");
      var btnTry = byId("btn-try-api");
      var btnDocs = byId("btn-open-docs");

      if (btnRandom) {
        btnRandom.addEventListener("click", function() {
          callEndpoint("/v1/random?n=16&fmt=hex");
        });
      }
      if (btnVrf) {
        btnVrf.addEventListener("click", function() {
          callEndpoint("/v1/vrf?sig=ecdsa");
        });
      }
      if (btnTry) {
        btnTry.addEventListener("click", function() {
          callEndpoint("/v1/random?n=16&fmt=hex");
        });
      }
      if (btnDocs) {
        btnDocs.addEventListener("click", function() {
          var base = (baseInput && baseInput.value.trim()) || origin;
          if (!base) base = origin;
          if (!base.startsWith("http")) base = "https://" + base;
          window.open(base.replace(/\\/$/, "") + "/docs", "_blank");
        });
      }
    })();
  </script>
</body>
</html>
"""


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def landing_page():
    return HTMLResponse(content=HOMEPAGE_HTML)


@app.get("/v1/health")
async def health():
    return {"ok": True}


@app.get("/v1/meta")
async def meta():
    return {
        "gateway_version": GATEWAY_VERSION,
        "core_url": CORE_URL,
        "vrf_url": VRF_URL,
    }


@app.get("/v1/random")
async def random_proxy(
    n: int,
    fmt: str = "hex",
    api_key: str = Depends(require_api_key),
):
    upstream = f"{CORE_URL.rstrip('/')}/random"
    params = {"n": n, "fmt": fmt}
    headers = {"X-API-Key": INTERNAL_R4_API_KEY}

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(upstream, params=params, headers=headers)

    return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/v1/vrf")
async def vrf_proxy(
    sig: str,
    api_key: str = Depends(require_api_key),
):
    # core VRF service: /random_dual?sig=ecdsa|dilithium
    upstream = f"{VRF_URL.rstrip('/')}/random_dual"
    params = {"sig": sig}
    headers = {"X-API-Key": INTERNAL_R4_API_KEY}

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(upstream, params=params, headers=headers)

    return JSONResponse(status_code=r.status_code, content=r.json())


@app.post("/v1/verify")
async def verify_signature(req: VerifyRequest):
    # Normalize and validate fields
    msg_hex = _clean_hex_64(req.msg_hash, "msg_hash")
    r_hex = _clean_hex_64(req.r, "r")
    s_hex = _clean_hex_64(req.s, "s")
    v_norm = _normalize_v(req.v)

    try:
        msg_bytes = binascii.unhexlify(msg_hex)
    except binascii.Error as e:
        raise HTTPException(
            status_code=400,
            detail=f"invalid msg_hash hex: {e}",
        )

    r_int = int(r_hex, 16)
    s_int = int(s_hex, 16)

    try:
        sig = keys.Signature(vrs=(v_norm, r_int, s_int))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"signature_init_failed: {type(e).__name__}: {e}",
        )

    try:
        recovered = Account.recover_hash(msg_bytes, signature=sig.to_bytes())
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"recover_failed: {type(e).__name__}: {e}",
        )

    recovered_norm = _normalize_address(recovered)
    expected_norm = _normalize_address(req.expected_signer)
    match = recovered_norm == expected_norm

    return {
        "ok": True,
        "match": match,
        "recovered": recovered,
        "expected": req.expected_signer,
        "v_used": v_norm,
    }
