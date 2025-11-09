#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8082}"
API_KEY="${API_KEY:-demo}"

echo "== /v1/health =="
curl -s "$BASE_URL/v1/health" && echo
echo

echo "== /v1/meta =="
curl -s "$BASE_URL/v1/meta" | jq .
echo

echo "== GET /v1/vrf?sig=ecdsa =="
curl -s -H "X-API-Key: $API_KEY" \
  "$BASE_URL/v1/vrf?sig=ecdsa" \
  -o /tmp/vrf.json
cat /tmp/vrf.json | jq .
echo

echo "== build verify payload =="
jq -n --slurpfile J /tmp/vrf.json '
  def clean: sub("^0x";"") | ascii_downcase | gsub("[^0-9a-f]";"");
  def pad64: (64 - length) as $n | if $n>0 then ("0"* $n)+. else . end;
  {
    msg_hash: ($J[0].msg_hash|tostring|clean|pad64),
    r:        ($J[0].r       |tostring|clean|pad64),
    s:        ($J[0].s       |tostring|clean|pad64),
    v:        ($J[0].v|tostring|tonumber),   # 27/28 — бекенд сам нормалізує
    expected_signer: ($J[0].signer_addr|tostring)
  }' > /tmp/verify_req.json

cat /tmp/verify_req.json | jq .
echo

echo "== POST /v1/verify =="
curl -sS -H "Accept: application/json" -H "Content-Type: application/json" \
     --data-binary @/tmp/verify_req.json \
     "$BASE_URL/v1/verify" | jq .
