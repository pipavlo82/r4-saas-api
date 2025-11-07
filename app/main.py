import os, json, math
from fastapi import FastAPI, Query, Header, HTTPException, Response
import httpx

app = FastAPI()

PORT = int(os.getenv("PORT", "8082"))
PUBLIC_API_KEY = os.getenv("PUBLIC_API_KEY", "demo")
CORE_URL = os.getenv("CORE_URL", "http://r4core:8080")
VRF_URL = os.getenv("VRF_URL", "http://r4core:8081")
INTERNAL_R4_API_KEY = os.getenv("INTERNAL_R4_API_KEY", PUBLIC_API_KEY)

@app.get("/v1/health")
async def health():
    return {"ok": True}

async def _core_random(n: int, fmt: str):
    async with httpx.AsyncClient(timeout=10) as client:
        return await client.get(
            f"{CORE_URL}/random",
            params={"n": n, "fmt": fmt},
            headers={"X-API-Key": INTERNAL_R4_API_KEY},
        )

async def _vrf_random(sig: str = "ecdsa"):
    async with httpx.AsyncClient(timeout=10) as client:
        return await client.get(
            f"{VRF_URL}/random_dual",
            params={"sig": sig},
            headers={"X-API-Key": INTERNAL_R4_API_KEY},
        )

@app.get("/v1/random")
async def random(n: int = Query(32, ge=1, le=4096), fmt: str = Query("hex")):
    # 1) core (:8080)/random — лише якщо 200 OK
    try:
        r = await _core_random(n=n, fmt=fmt)
        if r.status_code == 200:
            ctype = (r.headers.get("content-type") or "").lower()
            if fmt == "json":
                if "application/json" not in ctype:
                    hex_str = r.text.strip()
                    body = json.dumps({"hex": hex_str, "source": "core"})
                    return Response(content=body, status_code=200, media_type="application/json")
                return Response(content=r.content, status_code=200, media_type="application/json")
            return Response(content=r.content, status_code=200, media_type=r.headers.get("content-type", "text/plain"))
        # не 200 → йдемо у fallback
    except Exception:
        pass

    # 2) VRF fallback
    try:
        # Якщо хочуть JSON — віддамо одразу 1 32-бітне значення (як і раніше)
        if fmt == "json":
            vr = await _vrf_random("ecdsa")
            if vr.status_code != 200:
                return Response(json.dumps({"error": "core down; vrf fallback failed"}), 502, media_type="application/json")
            data = vr.json()
            rnd = int(data.get("random", 0))
            return Response(json.dumps({"random": rnd, "source": "vrf_fallback"}), 200, media_type="application/json")

        # fmt == hex → згенеруємо потрібну довжину, агрегуючи по 4 байти
        need = n
        chunks = bytearray()
        # скільки 4-байтових блоків потрібно
        blocks = math.ceil(need / 4)
        async with httpx.AsyncClient(timeout=10) as client:
            for _ in range(blocks):
                vr = await client.get(
                    f"{VRF_URL}/random_dual",
                    params={"sig": "ecdsa"},
                    headers={"X-API-Key": INTERNAL_R4_API_KEY},
                )
                if vr.status_code != 200:
                    return Response("core down; vrf fallback failed mid-aggregate", 502, media_type="text/plain")
                data = vr.json()
                rnd = int(data.get("random", 0))
                chunks.extend(rnd.to_bytes(4, "big"))
                if len(chunks) >= need:
                    break
        return Response(chunks[:need].hex(), 200, media_type="text/plain")
    except Exception:
        if fmt == "json":
            return Response(json.dumps({"error": "random endpoint unavailable"}), 502, media_type="application/json")
        return Response("random endpoint unavailable", 502, media_type="text/plain")

@app.get("/v1/vrf")
async def vrf(sig: str = Query("ecdsa"), x_api_key: str = Header(default="")):
    if x_api_key != PUBLIC_API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")
    r = await _vrf_random(sig)
    return Response(content=r.content, status_code=r.status_code, media_type=r.headers.get("content-type", "application/json"))
