from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from eth_keys import keys
from eth_utils import keccak, to_checksum_address

router = APIRouter()

class VerifyRequest(BaseModel):
    msg_hash: str          # 64 hex, без 0x
    r: str                 # 64 hex
    s: str                 # 64 hex
    v: int                 # 27/28 або 0/1
    expected_signer: str   # 0x... (чек-сумний чи ні — не критично)

def _clean_hex64(s: str, field: str) -> str:
    h = s.lower().lstrip("0x")
    if len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
        raise HTTPException(status_code=400, detail="msg_hash/r/s must be 64-hex (no 0x)")
    return h

@router.post("/v1/verify")
def verify(req: VerifyRequest):
    # нормалізація полів
    msg_hex = _clean_hex64(req.msg_hash, "msg_hash")
    r_hex   = _clean_hex64(req.r, "r")
    s_hex   = _clean_hex64(req.s, "s")

    # нормалізуємо v до {0,1}
    v = int(req.v)
    if v in (27, 28):
        v -= 27
    if v not in (0, 1):
        raise HTTPException(status_code=400, detail="v must be 0/1 or 27/28")

    # конвертації
    msg_hash_bytes = bytes.fromhex(msg_hex)
    r = int(r_hex, 16)
    s = int(s_hex, 16)

    try:
        sig = keys.Signature(vrs=(v, r, s))
        pub = sig.recover_public_key_from_msg_hash(msg_hash_bytes)
        recovered_addr = "0x" + keccak(pub.to_bytes())[-20:].hex()
        recovered_cs   = to_checksum_address(recovered_addr)
        expected_cs    = to_checksum_address(req.expected_signer)
        return {
            "ok": True,
            "match": recovered_cs == expected_cs,
            "recovered": recovered_cs,
            "expected": expected_cs,
            "v_used": v,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"verify_failed: {type(e).__name__}: {e}")
