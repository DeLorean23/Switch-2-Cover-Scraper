#!/usr/bin/python3
# Switch 2 Cover Scraper for Batocera
# Scrapes box art, screenshots, logos, fanart and game info for the
# "Switch 2" system from TheGamesDB (platform Nintendo Switch 2, id 5021)
# and writes them into /userdata/roms/switch2/gamelist.xml.
# Created by DeLorean23
# https://github.com/DeLorean23/Switch-2-Cover-Scraper
# License: MIT
import base64
import difflib
import json
import os
import re
import select
import shutil
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

VERSION = "@@VERSION@@"
API = "https://api.thegamesdb.net"
# TheGamesDB public API key of this project (may be replaced in the config file)
API_KEY = "59562402b802079ca854f0606dddf060de239ebdb808fecd65fc8c55be13aeae"
PLATFORM_S2 = 5021        # Nintendo Switch 2
PLATFORM_S1 = 4971        # Nintendo Switch (fallback, many games are on both)
REGION_ORDER = [6, 2, 1, 4]   # PAL, NTSC-U, NTSC, NTSC-J, then the rest

USERDATA = os.environ.get("S2CS_USERDATA", "/userdata")
ROM_DIR = os.path.join(USERDATA, "roms/switch2")
GAMELIST = os.path.join(ROM_DIR, "gamelist.xml")
IMG_DIR = os.path.join(ROM_DIR, "images")
CONF = os.path.join(USERDATA, "system/configs/switch2-cover-scraper.json")
CACHE_DIR = os.path.join(USERDATA, "system/switch2-cover-scraper")
LOG = os.path.join(USERDATA, "system/logs/switch2-cover-scraper.log")
PORTS_SCRIPT = os.environ.get("S2CS_SELF", "")

GAME_EXT = {".nsp", ".nsz", ".nup", ".xci", ".xcz", ".nca", ".nro", ".nso", ".kip"}
SKIP_DIRS = {"images", "videos", "manuals", "media", "downloaded_images", "downloaded_videos"}

# key, menu label, default
OPTIONS = [
    ("cover",      "Box cover (front)",                                         True),
    ("boxback",    "Box cover (back)",                                          False),
    ("screenshot", "Screenshot",                                                True),
    ("titleshot",  "Title screen",                                              False),
    ("logo",       "Logo",                                                      True),
    ("fanart",     "Fanart / background",                                       True),
    ("info",       "Game info (name, description, genre, developer, date ...)", True),
]
# option -> TheGamesDB image type (and side for box art), gamelist tag, file suffix
MEDIA = {
    "cover":      ("boxart", "front", "thumbnail", "thumb"),
    "boxback":    ("boxart", "back",  "boxback",   "boxback"),
    "screenshot": ("screenshot", None, "image",    "image"),
    "titleshot":  ("titlescreen", None, "titleshot", "titleshot"),
    "logo":       ("clearlogo", None, "marquee",   "marquee"),
    "fanart":     ("fanart", None,    "fanart",    "fanart"),
}
INFO_TAGS = ["name", "desc", "releasedate", "developer", "publisher", "genre", "players"]

CSI = "\033["
BANNER = base64.b64decode("@@BANNER@@").decode("utf-8")


# ---------------------------------------------------------------------------
# Logging / output
# ---------------------------------------------------------------------------
def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def say(msg=""):
    print(msg, flush=True)
    if msg:
        log(msg)


# ---------------------------------------------------------------------------
# Input: keyboard (raw terminal) + controller (evdev)
# ---------------------------------------------------------------------------
class Input:
    """Returns 'up', 'down', 'a', 'b' from keyboard or controller."""

    def __init__(self):
        self.devs = {}
        self.stick = {}
        self.tty = None
        try:
            from evdev import InputDevice, list_devices, ecodes
            self.e = ecodes
            for p in list_devices():
                try:
                    d = InputDevice(p)
                    keys = set(d.capabilities().get(ecodes.EV_KEY, []))
                    if ecodes.BTN_SOUTH in keys and ecodes.BTN_EAST in keys:
                        self.devs[d.fd] = d
                    else:
                        d.close()
                except Exception:
                    pass
        except Exception:
            self.e = None
        if sys.stdin.isatty():
            import termios
            import tty
            self.fd = sys.stdin.fileno()
            self.tty = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)

    def close(self):
        if self.tty is not None:
            import termios
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.tty)
            self.tty = None
        for d in self.devs.values():
            try:
                d.close()
            except Exception:
                pass
        self.devs = {}

    def _key(self):
        ch = os.read(self.fd, 1)
        if ch == b"\x1b":
            r, _, _ = select.select([self.fd], [], [], 0.05)
            if not r:
                return "b"
            seq = os.read(self.fd, 2)
            return {b"[A": "up", b"[B": "down", b"OA": "up", b"OB": "down"}.get(seq)
        return {b"\n": "a", b"\r": "a", b" ": "a", b"k": "up", b"j": "down",
                b"w": "up", b"s": "down", b"q": "b"}.get(ch)

    def _pad(self, d):
        e = self.e
        out = None
        for ev in d.read():
            if ev.type == e.EV_KEY and ev.value == 1:
                if ev.code == e.BTN_SOUTH:
                    out = "a"
                elif ev.code == e.BTN_EAST:
                    out = "b"
                elif ev.code == e.BTN_DPAD_UP:
                    out = "up"
                elif ev.code == e.BTN_DPAD_DOWN:
                    out = "down"
            elif ev.type == e.EV_ABS and ev.code == e.ABS_HAT0Y:
                if ev.value < 0:
                    out = "up"
                elif ev.value > 0:
                    out = "down"
            elif ev.type == e.EV_ABS and ev.code == e.ABS_Y:
                try:
                    info = d.absinfo(e.ABS_Y)
                    mid = (info.max + info.min) / 2
                    span = (info.max - info.min) / 2 or 1
                    pos = (ev.value - mid) / span
                except Exception:
                    continue
                state = -1 if pos < -0.6 else (1 if pos > 0.6 else 0)
                if state != self.stick.get(d.fd, 0):
                    self.stick[d.fd] = state
                    if state:
                        out = "up" if state < 0 else "down"
        return out

    def get(self):
        while True:
            fds = list(self.devs)
            if self.tty is not None:
                fds.append(self.fd)
            if not fds:
                return "a"
            r, _, _ = select.select(fds, [], [], 1.0)
            for fd in r:
                if self.tty is not None and fd == self.fd:
                    k = self._key()
                else:
                    try:
                        k = self._pad(self.devs[fd])
                    except OSError:
                        self.devs.pop(fd, None)
                        k = None
                if k:
                    return k

    def drain(self):
        """Forget buttons/keys pressed while the scraper was working."""
        for fd, d in list(self.devs.items()):
            try:
                while select.select([fd], [], [], 0)[0]:
                    list(d.read())
            except (OSError, BlockingIOError):
                pass
        if self.tty is not None:
            import termios
            termios.tcflush(self.fd, termios.TCIFLUSH)

    def wait(self, text="Press A / Enter to exit"):
        self.drain()
        print(text, flush=True)
        while self.get() not in ("a", "b"):
            pass


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def load_conf():
    conf = {k: d for k, _, d in OPTIONS}
    conf["overwrite"] = False
    try:
        with open(CONF, encoding="utf-8") as f:
            saved = json.load(f)
        for k in list(conf):
            if k in saved:
                conf[k] = bool(saved[k])
        if saved.get("apikey"):
            conf["apikey"] = str(saved["apikey"])
    except (OSError, ValueError):
        pass
    return conf


def save_conf(conf):
    os.makedirs(os.path.dirname(CONF), exist_ok=True)
    with open(CONF, "w", encoding="utf-8") as f:
        json.dump(conf, f, indent=2)


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------
def menu(conf, inp, game_count):
    keys = [k for k, _, _ in OPTIONS]
    items = ["all"] + keys + ["mode", "start", "exit"]
    pos = items.index("start")
    while True:
        out = [CSI + "2J" + CSI + "H" + BANNER, ""]
        out.append(f"  Games found in roms/switch2: {game_count}")
        out.append("  What should be scraped?   (Up/Down = move, A = select, B = exit)")
        out.append("")
        for i, it in enumerate(items):
            cur = "\033[1;35m>\033[0m" if i == pos else " "
            if it == "all":
                on = all(conf[k] for k in keys)
                line = f"[{'x' if on else ' '}] All"
            elif it in keys:
                label = dict((k, l) for k, l, _ in OPTIONS)[it]
                line = f"    [{'x' if conf[it] else ' '}] {label}"
            elif it == "mode":
                line = ("Mode: Re-scrape all games (overwrite)" if conf["overwrite"]
                        else "Mode: Only games / fields that are still missing")
                out.append("")
            elif it == "start":
                line = "\033[1;32mStart scraping\033[0m"
                out.append("")
            else:
                line = "Exit"
            out.append(f"  {cur} {line}")
        print("\n".join(out), flush=True)
        k = inp.get()
        if k == "up":
            pos = (pos - 1) % len(items)
        elif k == "down":
            pos = (pos + 1) % len(items)
        elif k == "b":
            return False
        elif k == "a":
            it = items[pos]
            if it == "all":
                on = not all(conf[x] for x in keys)
                for x in keys:
                    conf[x] = on
            elif it in keys:
                conf[it] = not conf[it]
            elif it == "mode":
                conf["overwrite"] = not conf["overwrite"]
            elif it == "start":
                if not any(conf[x] for x in keys):
                    continue
                return True
            else:
                return False


# ---------------------------------------------------------------------------
# Games and gamelist
# ---------------------------------------------------------------------------
def find_games():
    games = []
    for root, dirs, files in os.walk(ROM_DIR):
        rel_root = os.path.relpath(root, ROM_DIR)
        keep = []
        for d in sorted(dirs):
            if rel_root == "." and d.lower() in SKIP_DIRS:
                continue
            if d.lower().endswith(".s2"):
                games.append(os.path.normpath(os.path.join(rel_root, d)))
            elif not d.startswith("."):
                keep.append(d)
        dirs[:] = keep
        for f in sorted(files):
            if os.path.splitext(f)[1].lower() in GAME_EXT:
                games.append(os.path.normpath(os.path.join(rel_root, f)))
    return ["./" + g.replace(os.sep, "/") for g in games]


def load_gamelist():
    if os.path.exists(GAMELIST):
        try:
            tree = ET.parse(GAMELIST)
            return tree
        except ET.ParseError as ex:
            say(f"[WARNING] gamelist.xml could not be read ({ex}) - a backup is kept.")
            shutil.copy2(GAMELIST, GAMELIST + ".broken")
    return ET.ElementTree(ET.Element("gameList"))


def game_entry(root, path, create=False):
    for g in root.findall("game"):
        if (g.findtext("path") or "") == path:
            return g
    if not create:
        return None
    g = ET.SubElement(root, "game")
    ET.SubElement(g, "path").text = path
    return g


def get_tag(g, tag):
    if g is None:
        return ""
    return (g.findtext(tag) or "").strip()


def set_tag(g, tag, val):
    el = g.find(tag)
    if el is None:
        el = ET.SubElement(g, tag)
    el.text = val


def media_ok(g, tag):
    p = get_tag(g, tag)
    if not p:
        return False
    full = p if os.path.isabs(p) else os.path.join(ROM_DIR, p)
    return os.path.exists(full)


def clean_name(path):
    name = os.path.basename(path)
    stem, ext = os.path.splitext(name)
    if ext.lower() in GAME_EXT or ext.lower() == ".s2":
        name = stem
    name = re.sub(r"\[[^\]]*\]|\([^)]*\)|\{[^}]*\}", " ", name)
    name = re.sub(r"\b0100[0-9A-Fa-f]{12}\b", " ", name)
    name = re.sub(r"\bv\d+(\.\d+)*\b", " ", name, flags=re.I)
    name = name.replace("_", " ")
    return re.sub(r"\s+", " ", name).strip(" -.")


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ")
    s = re.sub(r"\bnintendo switch 2 edition\b|\bswitch 2 edition\b", " ", s)
    s = re.sub(r"^the\s+|,\s*the\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


# ---------------------------------------------------------------------------
# TheGamesDB
# ---------------------------------------------------------------------------
class ApiError(Exception):
    pass


class TGDB:
    def __init__(self, key):
        self.key = key
        self.remaining = None
        self.calls = 0

    def get(self, path, params):
        q = dict(params)
        q["apikey"] = self.key
        url = API + path + "?" + urllib.parse.urlencode(q)
        last = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": f"Switch2CoverScraper/{VERSION}"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as ex:
                body = ex.read().decode("utf-8", "replace")
                if ex.code in (401, 403):
                    raise ApiError("TheGamesDB refused the request (API key invalid or monthly limit used up). "
                                   f"HTTP {ex.code}: {body[:200]}")
                last = f"HTTP {ex.code}"
            except (urllib.error.URLError, OSError, ValueError) as ex:
                last = str(ex)
            time.sleep(2 * (attempt + 1))
        else:
            raise ApiError(f"No connection to TheGamesDB ({last}). Check the internet connection.")
        self.calls += 1
        if "remaining_monthly_allowance" in data:
            self.remaining = data.get("remaining_monthly_allowance", 0) + data.get("extra_allowance", 0)
        if data.get("code") != 200:
            raise ApiError(f"TheGamesDB: {data.get('status', 'error')}")
        return data

    def search(self, name, platform):
        d = self.get("/v1.1/Games/ByGameName", {
            "name": name,
            "filter[platform]": platform,
            "fields": "players,publishers,genres,overview",
        })
        return d.get("data", {}).get("games", []) or []

    def images(self, ids, types):
        out = {}
        base = None
        params = {"games_id": ",".join(str(i) for i in ids), "filter[type]": ",".join(sorted(types))}
        path = "/v1/Games/Images"
        page = 1
        while True:
            params["page"] = page
            d = self.get(path, params)
            data = d.get("data", {})
            base = base or data.get("base_url", {})
            for gid, imgs in (data.get("images") or {}).items():
                out.setdefault(int(gid), []).extend(imgs)
            nxt = (d.get("pages") or {}).get("next")
            if not nxt or page >= 10:
                break
            page += 1
        return base or {}, out

    def lookup(self, kind):
        """Genres / Developers / Publishers id -> name, cached for 30 days."""
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache = os.path.join(CACHE_DIR, f"{kind.lower()}.json")
        try:
            if time.time() - os.path.getmtime(cache) < 30 * 86400:
                with open(cache, encoding="utf-8") as f:
                    return json.load(f)
        except (OSError, ValueError):
            pass
        d = self.get(f"/v1/{kind}", {})
        items = d.get("data", {}).get(kind.lower(), {}) or {}
        table = {str(k): v.get("name", "") for k, v in items.items()}
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(table, f)
        return table


def pick(results, wanted):
    """Best result for the wanted name: name similarity, then region."""
    target = norm(wanted)
    best, best_key = None, None
    for g in results:
        title = g.get("game_title") or ""
        n = norm(title)
        if not n:
            continue
        score = difflib.SequenceMatcher(None, target, n).ratio()
        if n == target:
            score = 2.0
        elif n.startswith(target) or target.startswith(n):
            score = max(score, 0.9)
        reg = g.get("region_id")
        region = REGION_ORDER.index(reg) if reg in REGION_ORDER else len(REGION_ORDER)
        key = (score, -region)
        if best_key is None or key > best_key:
            best, best_key = g, key
    if best is None or best_key[0] < 0.75:
        return None
    return best


def load_misses():
    try:
        with open(os.path.join(CACHE_DIR, "notfound.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_misses(misses):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(os.path.join(CACHE_DIR, "notfound.json"), "w", encoding="utf-8") as f:
        json.dump(misses, f, indent=1)


def find_game(api, names):
    for platform in (PLATFORM_S2, PLATFORM_S1):
        for name in names:
            g = pick(api.search(name, platform), name)
            if g:
                return g, platform
    return None, None


def search_names(g, path):
    names = []
    base = clean_name(path)
    gl_name = get_tag(g, "name")
    for n in (gl_name, base):
        if n and n not in names:
            names.append(n)
    for n in list(names):
        short = re.split(r"\s*[:–—]\s*|\s+-\s+", n)[0].strip()
        if short and short != n and len(short) >= 4 and short not in names:
            names.append(short)
    return names


def download(url, dest):
    tmp = dest + ".part"
    req = urllib.request.Request(url, headers={"User-Agent": f"Switch2CoverScraper/{VERSION}"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f)
            if os.path.getsize(tmp) > 0:
                os.replace(tmp, dest)
                return True
        except (urllib.error.URLError, OSError):
            time.sleep(2 * (attempt + 1))
    try:
        os.remove(tmp)
    except OSError:
        pass
    return False


def choose_image(imgs, typ, side):
    cands = [i for i in imgs if i.get("type") == typ and (side is None or i.get("side") == side)]
    if not cands:
        return None
    cands.sort(key=lambda i: (i.get("id") or 0))
    return cands[0]


def file_stem(path):
    stem = os.path.basename(path.rstrip("/"))
    s, ext = os.path.splitext(stem)
    if ext.lower() in GAME_EXT or ext.lower() == ".s2":
        stem = s
    return re.sub(r'[\\/:*?"<>|]', "_", stem)


# ---------------------------------------------------------------------------
# Ports cover + EmulationStation reload
# ---------------------------------------------------------------------------
def update_ports_gamelist():
    if not PORTS_SCRIPT or not os.path.exists(PORTS_SCRIPT):
        return
    ports = os.path.dirname(PORTS_SCRIPT)
    name = os.path.basename(PORTS_SCRIPT)
    stem = os.path.splitext(name)[0]
    gl = os.path.join(ports, "gamelist.xml")
    image = f"./images/{stem}.jpg"
    if not os.path.exists(os.path.join(ports, image)):
        return
    try:
        tree = ET.parse(gl) if os.path.exists(gl) else ET.ElementTree(ET.Element("gameList"))
    except ET.ParseError:
        return
    root = tree.getroot()
    g = None
    for e in root.findall("game"):
        if os.path.basename(e.findtext("path") or "") == name:
            g = e
            break
    if g is None:
        g = ET.SubElement(root, "game")
        ET.SubElement(g, "path").text = "./" + name
    for tag, val in (("name", stem), ("image", image), ("thumbnail", image)):
        set_tag(g, tag, val)
    tree.write(gl, encoding="utf-8", xml_declaration=True)


def reload_es():
    try:
        urllib.request.urlopen("http://127.0.0.1:1234/reloadgames", timeout=5).read()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Main work
# ---------------------------------------------------------------------------
def scrape(conf):
    selected = [k for k, _, _ in OPTIONS if conf.get(k)]
    overwrite = conf.get("overwrite", False)
    api = TGDB(conf.get("apikey") or API_KEY)

    paths = find_games()
    tree = load_gamelist()
    root = tree.getroot()

    # what does every game still need?
    todo = []
    for p in paths:
        g = game_entry(root, p)
        need = []
        for k in selected:
            if overwrite:
                need.append(k)
            elif k in MEDIA:
                if not media_ok(g, MEDIA[k][2]):
                    need.append(k)
            elif k == "info":
                if not get_tag(g, "desc") or not get_tag(g, "name"):
                    need.append(k)
        if need:
            todo.append((p, need))

    say(f"Games in roms/switch2: {len(paths)}   to scrape: {len(todo)}   "
        f"mode: {'re-scrape all' if overwrite else 'only missing'}")
    say("")
    if not todo:
        say("Nothing to do - every game already has the selected items.")
        return api, 0, 0, []

    # 1. find every game on TheGamesDB
    # (games not found in the last 7 days are skipped in "only missing" mode,
    #  so they don't use up the monthly TheGamesDB requests on every run)
    matches = {}
    not_found = []
    misses = load_misses()
    now = time.time()
    for n, (p, need) in enumerate(todo, 1):
        g = game_entry(root, p)
        names = search_names(g, p)
        label = names[0] if names else p
        miss_key = p + "|" + "|".join(names)
        if not overwrite and now - misses.get(miss_key, 0) < 7 * 86400:
            not_found.append(label)
            say(f"[{n}/{len(todo)}] {label} ... not found (checked in the last 7 days)")
            continue
        print(f"[{n}/{len(todo)}] {label} ... ", end="", flush=True)
        try:
            hit, platform = find_game(api, names)
        except ApiError:
            say("")
            raise
        if hit:
            misses.pop(miss_key, None)
            matches[p] = hit
            where = "Switch 2" if platform == PLATFORM_S2 else "Switch"
            say(f"found: {hit.get('game_title')} ({where})")
        else:
            not_found.append(label)
            misses[miss_key] = now
            say("not found")
    save_misses(misses)

    if not matches:
        return api, 0, len(todo), not_found

    # 2. images for all found games (in batches)
    types = {MEDIA[k][0] for k in selected if k in MEDIA}
    base, images = {}, {}
    ids = sorted({m["id"] for m in matches.values()})
    if types:
        for i in range(0, len(ids), 20):
            b, im = api.images(ids[i:i + 20], types)
            base = base or b
            images.update(im)

    # 3. names for genres / developers / publishers
    lookups = {}
    if "info" in selected:
        for kind in ("Genres", "Developers", "Publishers"):
            try:
                lookups[kind] = api.lookup(kind)
            except ApiError as ex:
                say(f"[WARNING] {kind} list not available: {ex}")
                lookups[kind] = {}

    # 4. download and write gamelist
    os.makedirs(IMG_DIR, exist_ok=True)
    if os.path.exists(GAMELIST):
        shutil.copy2(GAMELIST, GAMELIST + ".bak")
    say("")
    say("Downloading ...")
    done = 0
    for p, need in todo:
        hit = matches.get(p)
        if not hit:
            continue
        g = game_entry(root, p, create=True)
        stem = file_stem(p)
        got = []
        imgs = images.get(int(hit["id"]), [])
        for k in need:
            if k not in MEDIA:
                continue
            typ, side, tag, suffix = MEDIA[k]
            img = choose_image(imgs, typ, side)
            if not img:
                continue
            fn = img.get("filename", "")
            ext = os.path.splitext(fn)[1].lower() or ".jpg"
            size = "original" if typ == "clearlogo" else "large"
            url = (base.get(size) or base.get("original") or "https://cdn.thegamesdb.net/images/original/") + fn
            dest = os.path.join(IMG_DIR, f"{stem}-{suffix}{ext}")
            if download(url, dest):
                set_tag(g, tag, f"./images/{stem}-{suffix}{ext}")
                got.append(k)
        # without a screenshot the cover is used as main image
        if "cover" in got and not media_ok(g, "image"):
            set_tag(g, "image", get_tag(g, "thumbnail"))
        if "info" in need:
            title = hit.get("game_title") or ""
            if title and (overwrite or not get_tag(g, "name")):
                set_tag(g, "name", title)
            fields = {
                "desc": (hit.get("overview") or "").strip(),
                "releasedate": "",
                "developer": ", ".join(filter(None, (lookups.get("Developers", {}).get(str(x), "")
                                                     for x in hit.get("developers") or []))),
                "publisher": ", ".join(filter(None, (lookups.get("Publishers", {}).get(str(x), "")
                                                     for x in hit.get("publishers") or []))),
                "genre": ", ".join(filter(None, (lookups.get("Genres", {}).get(str(x), "")
                                                 for x in hit.get("genres") or []))),
                "players": "",
            }
            rd = hit.get("release_date") or ""
            if re.match(r"^\d{4}-\d{2}-\d{2}$", rd):
                fields["releasedate"] = rd.replace("-", "") + "T000000"
            pl = hit.get("players")
            if isinstance(pl, int) and pl > 0:
                fields["players"] = "1" if pl == 1 else f"1-{pl}"
            for tag, val in fields.items():
                if val and (overwrite or not get_tag(g, tag)):
                    set_tag(g, tag, val)
            got.append("info")
        done += 1
        say(f"  {hit.get('game_title')}: {', '.join(got) if got else 'no media available'}")

    try:
        ET.indent(tree, space="\t")
    except AttributeError:
        pass
    tree.write(GAMELIST, encoding="utf-8", xml_declaration=True)
    return api, done, len(todo), not_found


def main():
    auto = "--auto" in sys.argv
    inp = None if auto else Input()
    exit_code = 0
    try:
        if not os.path.isdir(ROM_DIR):
            print(BANNER)
            say(f"[ERROR] {ROM_DIR} not found.")
            say("Install the Switch 2 system first (e.g. with the All-In Installer & Update).")
            return 1
        conf = load_conf()
        if not auto:
            if not menu(conf, inp, len(find_games())):
                return 0
            save_conf(conf)
        print(CSI + "2J" + CSI + "H" + BANNER + "\n", flush=True)
        log(f"===== Switch 2 Cover Scraper {VERSION} =====")
        try:
            api, done, total, not_found = scrape(conf)
        except ApiError as ex:
            say("")
            say(f"[ERROR] {ex}")
            exit_code = 1
        else:
            say("")
            say(f"Done: {done} game(s) scraped.")
            if not_found:
                say(f"Not found on TheGamesDB ({len(not_found)}): " + ", ".join(not_found))
                say("Tip: rename the game folder/file to the exact game title and run the scraper again.")
            if api.remaining is not None:
                say(f"TheGamesDB requests left this month: {api.remaining}")
        update_ports_gamelist()
        if reload_es():
            say("The game list is being reloaded in EmulationStation.")
        else:
            say("Reload the game list in EmulationStation (Start > Game settings > Update gamelists).")
        say(f"Log: {LOG}")
        print()
        if inp:
            inp.wait()
        return exit_code
    finally:
        if inp:
            inp.close()


if __name__ == "__main__":
    sys.exit(main())
