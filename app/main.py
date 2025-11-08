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
