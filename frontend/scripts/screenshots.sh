#!/usr/bin/env bash
# Screenshot every screen of the demo build in light and dark, at phone and desktop width.
# Usage: bash frontend/scripts/screenshots.sh <out-dir> [comma-separated name filters]
# Needs Docker; uses node:24.21.0-bookworm-slim and the Playwright image.
set -euo pipefail
out=$(cd "${1:?out dir}" && pwd)
filter=${2:-}
frontend=$(cd "$(dirname "$0")/.." && pwd)
net="ataraxia-shots-$$"
docker network create "$net" >/dev/null
cleanup() {
  docker rm -f "$net-vite" >/dev/null 2>&1 || true
  docker network rm "$net" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker run -d --rm --name "$net-vite" --network "$net" --network-alias frontend -e VITE_DEMO=1 \
  -v "$frontend:/app" -w /app node:24.21.0-bookworm-slim \
  npx vite --host 0.0.0.0 --port 8080 --strictPort >/dev/null
docker run --rm --network "$net" -v "$frontend/scripts:/scripts:ro" -v "$out:/out" \
  mcr.microsoft.com/playwright:v1.56.1-noble sh -ec "
    cd /tmp && npm init -y >/dev/null && npm i --silent playwright@1.56.1 >/dev/null
    cp /scripts/screenshots.mjs .
    node -e \"(async()=>{for(let i=0;i<60;i++){try{if((await fetch('http://frontend:8080/')).ok)return}catch{}await new Promise(r=>setTimeout(r,1000))}process.exit(1)})()\"
    node screenshots.mjs http://frontend:8080 /out '$filter'"
