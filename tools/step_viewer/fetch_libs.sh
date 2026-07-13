#!/usr/bin/env bash
# Vendor the STEP viewer runtime: Online3DViewer engine + occt-import-js WASM.
#
# Online3DViewer 0.18.0 hardcodes a jsdelivr CDN URL for the occt-import-js
# worker (no public override), so after vendoring we patch that one string to
# the localhost URL below. The origin must match how the repo is served —
# tools/step_viewer/README note: python3 -m http.server 8123 from repo root.
set -euo pipefail

O3DV_VERSION=0.18.0
OCCT_VERSION=0.0.22   # must match the version pinned inside the o3dv engine
LOCAL_LIBS_URL="http://localhost:8123/tools/step_viewer/vendor/libs/"

cd "$(dirname "$0")"
rm -rf vendor
mkdir -p vendor/libs
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

curl -sL "https://registry.npmjs.org/online-3d-viewer/-/online-3d-viewer-${O3DV_VERSION}.tgz" \
    | tar xz -C "$tmp" package/build/engine/o3dv.min.js
curl -sL "https://registry.npmjs.org/occt-import-js/-/occt-import-js-${OCCT_VERSION}.tgz" \
    | tar xz -C "$tmp" package/dist

sed "s|https://cdn.jsdelivr.net/npm/occt-import-js@${OCCT_VERSION}/dist/|${LOCAL_LIBS_URL}|g" \
    "$tmp/package/build/engine/o3dv.min.js" > vendor/o3dv.min.js
grep -q "$LOCAL_LIBS_URL" vendor/o3dv.min.js || { echo "patch failed: CDN URL not found"; exit 1; }

cp "$tmp"/package/dist/occt-import-js-worker.js \
   "$tmp"/package/dist/occt-import-js.js \
   "$tmp"/package/dist/occt-import-js.wasm \
   "$tmp"/package/dist/license.* \
   vendor/libs/

echo "vendored: $(du -sh vendor | cut -f1) in $(pwd)/vendor"
