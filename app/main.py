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
    want_json = (fmt.lower() == "json")
    core_fmt = "hex"  # завжди тягнемо HEX з core, а JSON формуємо тут

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
                return {"hex": hex_str, "n": n, "source": "core"}
            return Response(content=hex_str, media_type="text/plain", status_code=200)
        else:
            # core відповів помилкою → піде в fallback
            raise RuntimeError(f"core returned {r.status_code}")
    except Exception:
        # Fallback: беремо 4 байти з VRF (:8081)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                rr = await client.get(
                    f"{VRF_URL}/random_dual",
                    params={"sig": "ecdsa"},
                    headers={"X-API-Key": INTERNAL_R4_API_KEY},
                )
            if rr.status_code == 200:
                j = rr.json()
                seed4 = int(j.get("random", 0)) & 0xFFFFFFFF
                hx = seed4.to_bytes(4, "big").hex()
                if want_json:
                    return {"random": seed4, "hex": hx, "source": "vrf_fallback"}
                return Response(content=hx, media_type="text/plain", status_code=200)
        except Exception:
            pass

        return Response(
            content="core (:8080) is unavailable. VRF fallback can supply only 4 bytes; please enable core for longer outputs.",
            media_type="text/plain",
            status_code=503,
        )

@app.get("/v1/vrf")
async def vrf(sig: str = Query("ecdsa"), x_api_key: str = Header(default="")):
    if x_api_key != PUBLIC_API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")
    r = await _vrf_random(sig)
    return Response(content=r.content, status_code=r.status_code, media_type=r.headers.get("content-type", "application/json"))
