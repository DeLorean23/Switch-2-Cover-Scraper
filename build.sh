#!/bin/bash
# Builds the ready-to-use Ports script and its ZIP into dist/
#   dist/Switch 2 Cover Scraper.zip
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
DIST="$ROOT/dist"
NAME="Switch 2 Cover Scraper"
VERSION="${1:-$(tr -d ' \r\n' < "$ROOT/VERSION")}"

rm -rf "$DIST"
STAGE="$DIST/stage"
mkdir -p "$STAGE/roms/ports/images"
python3 - "$ROOT" "$STAGE/roms/ports/$NAME.sh" "$VERSION" <<'PY'
import base64, sys
root, out, ver = sys.argv[1:4]
py = open(root + "/src/scraper.py", encoding="utf-8").read()
banner = open(root + "/src/banner.txt", "rb").read()
for key, val in {"@@VERSION@@": ver,
                 "@@BANNER@@": base64.b64encode(banner).decode()}.items():
    assert key in py, key
    py = py.replace(key, val)
assert "@@" not in py
compile(py, "scraper.py", "exec")
t = open(root + "/src/launcher.template.sh", encoding="utf-8").read()
t = t.replace("@@VERSION@@", ver)
t = t.replace("@@SCRAPER@@", base64.encodebytes(py.encode("utf-8")).decode().rstrip("\n"))
assert "@@" not in t
open(out, "w", newline="\n", encoding="utf-8").write(t)
PY
chmod +x "$STAGE/roms/ports/$NAME.sh"
bash -n "$STAGE/roms/ports/$NAME.sh"
cp "$ROOT/assets/cover.jpg" "$STAGE/roms/ports/images/$NAME.jpg"
cp "$ROOT/README.md" "$STAGE/README.txt"
cp "$ROOT/LIESMICH.md" "$STAGE/LIESMICH.txt"
(cd "$STAGE" && zip -qr "$DIST/$NAME.zip" README.txt LIESMICH.txt roms)
cp "$STAGE/roms/ports/$NAME.sh" "$DIST/"
rm -rf "$STAGE"
echo "built: dist/$NAME.zip"
