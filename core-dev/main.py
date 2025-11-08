from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse, JSONResponse
import secrets

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/random")
def random(n: int = Query(32, ge=1, le=4096), fmt: str = Query("hex")):
    # dev-core: це ТИМЧАСОВИЙ генератор (os.urandom) для локальних тестів gateway
    raw = secrets.token_bytes(n)
    if fmt.lower() == "hex":
        return PlainTextResponse(raw.hex(), media_type="text/plain")
    # "json": віддаємо так само, як робить gateway при прозорому режимі
    return JSONResponse({"hex": raw.hex(), "n": n, "source": "core-dev"})
