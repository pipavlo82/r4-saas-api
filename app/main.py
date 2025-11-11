from pathlib import Path
import os
import time
import asyncio
from typing import Dict, Tuple

import httpx
from fastapi import (
    FastAPI,
    Query,
    Header,
    HTTPException,
    Response,
    Request,
    Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.verify_route import router as verify_router

# --------------------------------------------------------------------
#  Base settings
# --------------------------------------------------------------------

app = FastAPI(
    title="R4 SaaS API",
    version=os.getenv("GATEWAY_VERSION", "v0.1.3"),
)

PORT = int(os.getenv("PORT", "8082"))
PUBLIC_API_KEY = os.getenv("PUBLIC_API_KEY", "demo")
CORE_URL = os.getenv("CORE_URL", "http://r4core:8080")
VRF_URL = os.getenv("VRF_URL", "http://r4core:8081")
INTERNAL_R4_API_KEY = os.getenv("INTERNAL_R4_API_KEY", PUBLIC_API_KEY)

app.include_router(verify_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------
#  Simple token-bucket rate limiting
# --------------------------------------------------------------------

BUCKET: Dict[Tuple[str, str], Tuple[int, float]] = {}
LOCK = asyncio.Lock()
LIMITS = {
    "default": (60, 60.0),
    "vrf": (30, 60.0),
}


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
            raise HTTPException(
                status_code=429,
                detail=f"rate limit exceeded; retry in ~{retry}s",
            )
        BUCKET[key] = (cur_tokens - 1, reset_ts)


async def rl_default(request: Request):
    await check_rate(request, "default")


async def rl_vrf(request: Request):
    await check_rate(request, "vrf")


# --------------------------------------------------------------------
#  Landing page (marketing + live playground)
# --------------------------------------------------------------------

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
      --text: #e5e7eb;
      --muted: #9ca3af;
      --border: #1f2937;
      --error: #f97373;
      --good: #4ade80;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background: radial-gradient(circle at top left, #0f172a 0, var(--bg) 50%, #000 100%);
    }
    .page {
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 16px 64px;
    }
    .hero {
      display: flex;
      flex-wrap: wrap;
      gap: 24px;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 32px;
    }
    .hero-main {
      max-width: 560px;
    }
    .hero-kpi {
      padding: 16px 20px;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid rgba(148, 163, 184, 0.3);
      font-size: 13px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .hero-kpi span.tag {
      padding: 2px 8px;
      border-radius: 999px;
      background: rgba(22, 163, 74, 0.15);
      color: #bbf7d0;
      font-weight: 500;
      font-size: 12px;
    }
    h1 {
      font-size: 32px;
      line-height: 1.1;
      margin: 16px 0 12px;
    }
    .hero-sub {
      font-size: 15px;
      color: var(--muted);
      max-width: 520px;
    }
    .hero-buttons {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 20px;
    }
    .btn-pill {
      border-radius: 999px;
      border: none;
      cursor: pointer;
      padding: 10px 22px;
      font-size: 14px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      background: linear-gradient(90deg, var(--accent1), var(--accent2));
      color: #000;
      box-shadow: 0 10px 30px rgba(6, 182, 212, 0.35);
      transition: transform 0.12s ease, box-shadow 0.12s ease, filter 0.15s ease;
      text-decoration: none;
    }
    .btn-pill:hover {
      transform: translateY(-1px);
      filter: brightness(1.05);
      box-shadow: 0 16px 40px rgba(6, 182, 212, 0.45);
    }
    .btn-ghost {
      border-radius: 999px;
      border: 1px solid rgba(148, 163, 184, 0.6);
      background: rgba(15, 23, 42, 0.7);
      color: var(--text);
      padding: 10px 18px;
      font-size: 14px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: background 0.12s ease, border-color 0.12s ease;
    }
    .btn-ghost:hover {
      background: rgba(15, 23, 42, 0.9);
      border-color: #e5e7eb;
    }
    .hero-side {
      flex: 1 1 260px;
      max-width: 360px;
    }
    .card {
      background: radial-gradient(circle at top left, #0f172a 0, var(--card) 40%, var(--card2) 100%);
      border-radius: 20px;
      border: 1px solid var(--border);
      padding: 18px 18px 16px;
      box-shadow: 0 20px 60px rgba(15, 23, 42, 0.85);
    }
    .card h2 {
      font-size: 15px;
      margin: 0 0 4px;
    }
    .card p {
      margin: 0 0 12px;
      font-size: 13px;
      color: var(--muted);
    }
    .pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 12px;
      font-size: 11px;
    }
    .pill {
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid rgba(148, 163, 184, 0.5);
      color: var(--muted);
    }
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 8px;
    }
    .metric {
      padding: 10px 10px 8px;
      border-radius: 12px;
      background: rgba(15, 23, 42, 0.9);
      border: 1px dashed rgba(55, 65, 81, 0.8);
    }
    .metric-label {
      font-size: 11px;
      color: var(--muted);
      margin-bottom: 4px;
    }
    .metric-value {
      font-size: 14px;
      font-weight: 600;
    }
    .metric-tag {
      font-size: 10px;
      color: #22c55e;
      margin-top: 2px;
    }
    .section {
      margin-top: 30px;
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
      gap: 24px;
    }
    .section h3 {
      font-size: 16px;
      margin-top: 0;
      margin-bottom: 8px;
    }
    .section p {
      font-size: 13px;
      color: var(--muted);
      margin: 4px 0;
    }
    .code-card {
      background: #020617;
      border-radius: 16px;
      border: 1px solid rgba(30, 64, 175, 0.8);
      padding: 14px 14px;
      font-family: "JetBrains Mono", Menlo, ui-monospace, SFMono-Regular, monospace;
      font-size: 12px;
      color: #e5e7eb;
      position: relative;
      overflow: hidden;
    }
    .code-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      color: var(--muted);
      margin-bottom: 8px;
    }
    .code-body {
      white-space: pre;
      overflow-x: auto;
      max-height: 260px;
    }
    .code-badge {
      font-size: 10px;
      padding: 3px 8px;
      border-radius: 999px;
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.5);
      color: #6ee7b7;
    }
    .controls {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }
    .input {
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid rgba(55, 65, 81, 0.9);
      border-radius: 999px;
      padding: 6px 10px;
      color: var(--text);
      font-size: 12px;
      min-width: 0;
    }
    .input:focus {
      outline: none;
      border-color: #22c55e;
      box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.5);
    }
    .log {
      margin-top: 10px;
      padding: 8px 10px;
      border-radius: 10px;
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid rgba(31, 41, 55, 0.9);
      font-family: "JetBrains Mono", ui-monospace;
      font-size: 11px;
      max-height: 220px;
      overflow: auto;
      white-space: pre-wrap;
    }
    .log-line.ok { color: var(--good); }
    .log-line.error { color: var(--error); }
    .log-line.meta { color: var(--muted); }
    @media (max-width: 840px) {
      .section { grid-template-columns: minmax(0, 1fr); }
      .hero { flex-direction: column; align-items: flex-start; }
      .hero-side { max-width: none; width: 100%; }
    }
  </style>
</head>
<body>
  <div class="page">
    <header class="hero">
      <div class="hero-main">
        <div class="hero-kpi">
          <span class="tag">RE4CTOR Gateway</span>
          <span>30–50ms dev latency • 600× faster than on-chain oracles</span>
        </div>
        <h1>FIPS-ready randomness API with verifiable proofs.</h1>
        <p class="hero-sub">
          RE4CTOR SaaS API is a hardened HTTP gateway in front of RE4CTOR Core RNG and dual-signature VRF.
          One endpoint for crypto, gaming, and defense workloads.
        </p>
        <div class="hero-buttons">
          <a href="#liveSection" id="btnTry" class="btn-pill">Try live API</a>
          <button id="btnDocs" class="btn-ghost">Open Swagger /docs</button>
        </div>
      </div>

      <div class="hero-side">
        <div class="card">
          <h2>Runtime snapshot</h2>
          <p>Live view into your local RE4CTOR SaaS gateway.</p>
          <div class="pill-row">
            <div class="pill">FIPS 204-ready 🔐</div>
            <div class="pill">Post-quantum combo (ML-DSA-65)</div>
            <div class="pill">On-chain proof friendly</div>
          </div>
          <div class="metrics-grid">
            <div class="metric">
              <div class="metric-label">Latency (dev)</div>
              <div class="metric-value" id="latencyMetric">~30–50 ms</div>
              <div class="metric-tag">Gateway ↔ Core</div>
            </div>
            <div class="metric">
              <div class="metric-label">VRF</div>
              <div class="metric-value">ECDSA + ML-DSA-65</div>
              <div class="metric-tag">Dual-signed</div>
            </div>
            <div class="metric">
              <div class="metric-label">Plan</div>
              <div class="metric-value" id="planMetric">dev</div>
              <div class="metric-tag">X-R4-* headers</div>
            </div>
          </div>
        </div>
      </div>
    </header>

    <section class="section" id="liveSection">
      <div>
        <h3>Live API playground</h3>
        <p>
          Use your local gateway on <code>http://localhost:8082</code> to pull randomness and VRF proofs.
          All calls go directly from your browser → gateway → RE4CTOR Core.
        </p>
        <div class="controls">
          <input id="baseUrl" class="input" style="flex: 1 1 180px"
                 value="http://localhost:8082"
                 placeholder="Gateway base URL" />
          <input id="apiKey" class="input" style="flex: 1 1 140px"
                 value="demo"
                 placeholder="X-API-Key" />
        </div>
        <div class="hero-buttons" style="margin-top: 8px;">
          <button id="btnRandom" class="btn-pill">Call /v1/random</button>
          <button id="btnVrf" class="btn-ghost">Call /v1/vrf?sig=ecdsa</button>
        </div>
        <div class="log" id="logBox">
          <div class="log-line meta">
            Ready. Click “Call /v1/random” or “Call /v1/vrf?sig=ecdsa”.
          </div>
        </div>
      </div>

      <div>
        <div class="code-card">
          <div class="code-header">
            <span>curl example</span>
            <span class="code-badge">copy-paste into terminal</span>
          </div>
          <div class="code-body" id="codeBlock">
curl -s -H "X-API-Key: demo" \\
  "http://localhost:8082/v1/random?n=16&fmt=hex"

curl -s -H "X-API-Key: demo" \\
  "http://localhost:8082/v1/vrf?sig=ecdsa" | jq .
          </div>
        </div>
      </div>
    </section>
  </div>

  <script>
    function $(id) {
      return document.getElementById(id);
    }

    window.addEventListener("DOMContentLoaded", function () {
      var logBox = $("logBox");

      function log(line, type) {
        if (!logBox) return;
        var div = document.createElement("div");
        div.className = "log-line " + (type || "meta");
        div.textContent = line;
        logBox.appendChild(div);
        logBox.scrollTop = logBox.scrollHeight;
      }

      async function callEndpoint(path) {
        var baseInput = $("baseUrl");
        var apiInput  = $("apiKey");

        var baseUrl = (baseInput && baseInput.value) ? baseInput.value : window.location.origin;
        var apiKey  = (apiInput && apiInput.value)  ? apiInput.value  : "demo";

        if (baseUrl.charAt(baseUrl.length - 1) === "/") {
          baseUrl = baseUrl.slice(0, -1);
        }
        var url = baseUrl + path;

        var start = performance.now();
        log("→ GET " + url, "meta");

        try {
          var res  = await fetch(url, { headers: { "X-API-Key": apiKey } });
          var text = await res.text();
          var dt   = Math.round(performance.now() - start);

          var plan = res.headers.get("x-r4-plan");
          if (plan) {
            var planMetric = $("planMetric");
            if (planMetric) {
              planMetric.textContent = plan;
            }
          }
          var latMetric = $("latencyMetric");
          if (latMetric) {
            latMetric.textContent = dt + " ms";
          }

          log("← " + res.status + " " + res.statusText + " (" + dt + " ms)", res.ok ? "ok" : "error");
          log(text, res.ok ? "meta" : "error");
        } catch (err) {
          log("ERROR: " + err, "error");
          console.error("RE4CTOR playground error:", err);
        }
      }

      var btnRandom = $("btnRandom");
      if (btnRandom) {
        btnRandom.addEventListener("click", function () {
          callEndpoint("/v1/random?n=16&fmt=hex");
        });
      }

      var btnVrf = $("btnVrf");
      if (btnVrf) {
        btnVrf.addEventListener("click", function () {
          callEndpoint("/v1/vrf?sig=ecdsa");
        });
      }

      var btnDocs = $("btnDocs");
      if (btnDocs) {
        btnDocs.addEventListener("click", function () {
          var baseInput = $("baseUrl");
          var baseUrl = (baseInput && baseInput.value) ? baseInput.value : window.location.origin;
          if (baseUrl.charAt(baseUrl.length - 1) === "/") {
            baseUrl = baseUrl.slice(0, -1);
          }
          window.open(baseUrl + "/docs", "_blank");
        });
      }

      var btnTry = $("btnTry");
      if (btnTry) {
        btnTry.addEventListener("click", function (e) {
          // якір уже веде на #liveSection, додаємо smooth-scroll
          e.preventDefault();
          var section = document.getElementById("liveSection");
          if (section && section.scrollIntoView) {
            section.scrollIntoView({ behavior: "smooth", block: "start" });
          } else {
            window.location.hash = "#liveSection";
          }
        });
      }
    });
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page():
    return HTMLResponse(content=HOMEPAGE_HTML)


# --------------------------------------------------------------------
#  API endpoints
# --------------------------------------------------------------------

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
async def random_endpoint(
    request: Request,
    n: int = Query(32, ge=1, le=4096),
    fmt: str = Query("hex"),
    x_api_key: str = Header(default=""),
    _: None = Depends(rl_default),
):
    if x_api_key != PUBLIC_API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

    want_json = fmt.lower() == "json"
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
            return Response(
                content=hex_str,
                media_type="text/plain",
                status_code=200,
            )
        else:
            raise RuntimeError(f"core returned {r.status_code}")
    except Exception:
        # Fallback на VRF node (4 байти)
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
                    return {
                        "random": seed,
                        "hex": hex4,
                        "source": "vrf_fallback",
                    }
                return Response(
                    content=hex4,
                    media_type="text/plain",
                    status_code=200,
                )
        except Exception:
            pass

        return Response(
            content=(
                "core (:8080) is unavailable. "
                "VRF fallback can supply only 4 bytes; "
                "please enable core for longer outputs."
            ),
            media_type="text/plain",
            status_code=503,
        )


@app.get("/v1/vrf")
async def vrf_endpoint(
    request: Request,
    sig: str = Query("ecdsa"),
    x_api_key: str = Header(default=""),
    _: None = Depends(rl_vrf),
):
    if x_api_key != PUBLIC_API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{VRF_URL}/random_dual",
            params={"sig": sig},
            headers={"X-API-Key": INTERNAL_R4_API_KEY},
        )
    return Response(
        content=r.content,
        status_code=r.status_code,
        media_type=r.headers.get("content-type", "application/json"),
    )
