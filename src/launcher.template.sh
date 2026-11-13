#!/bin/bash
# Switch 2 Cover Scraper for Batocera v43
# Scrapes box art, screenshots, logos, fanart and game info for the system
# "Switch 2" (/userdata/roms/switch2) from TheGamesDB (platform Nintendo Switch 2).
# Choose in the menu what should be scraped - with the controller or the keyboard.
# Created by DeLorean23
# https://github.com/DeLorean23/Switch-2-Cover-Scraper
# License: MIT

SCRAPER_VERSION="@@VERSION@@"

SELF="$(readlink -f "$0")"
LOG_DIR="/userdata/system/logs"
LOG="$LOG_DIR/switch2-cover-scraper.log"

# Open a visible terminal window (Ports scripts run without one by default)
if [[ "${1:-}" != "--in-terminal" ]]; then
    mkdir -p "$LOG_DIR"
    export DISPLAY="${DISPLAY:-:0.0}"
    if command -v xterm >/dev/null 2>&1; then
        exec xterm -fullscreen -fa "Monospace" -fs 12 -bg black -fg white \
            -T "Switch 2 Cover Scraper" -e /bin/bash "$SELF" --in-terminal
    fi
    echo "xterm not found - cannot open a terminal window." >> "$LOG"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 not found."
    sleep 10
    exit 1
fi

PY="$(mktemp /tmp/switch2-cover-scraper-XXXX.py)"
awk '$0=="__SCRAPER_BEGIN__"{f=1;next} $0=="__SCRAPER_END__"{f=0} f' "$SELF" | base64 -d > "$PY"
S2CS_SELF="$SELF" python3 "$PY"
rc=$?
rm -f "$PY"
exit $rc

__SCRAPER_BEGIN__
@@SCRAPER@@
__SCRAPER_END__
