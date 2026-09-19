# -*- coding: utf-8 -*-
"""
Fotograma · app móvil de películas, series y anime desde Blogger.
Versión Flet (Flutter + Python) — compatible Flet 0.21 → 0.28+.
"""
import asyncio
import base64
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import flet as ft

try:
    import flet_video as ftv
    HAS_FTVIDEO = True
except ImportError:
    HAS_FTVIDEO = False

try:
    import flet_webview as fwv
    HAS_FTWEBVIEW = True
except ImportError:
    fwv = None
    HAS_FTWEBVIEW = False

BLOG_URL = "https://sdfmngcggcjsaklngfjkd.blogspot.com".rstrip("/")


# =========================================================================
#  🩹 CONSTRUCTORES UNIVERSALES (Padding / Margin / Border / BorderSide)
#  Detectan automáticamente qué API expone tu Flet y devuelven lo que sea
#  válido. No crashean en ninguna versión.
# =========================================================================
def _mk_inset(kind, l=0, t=0, r=0, b=0):
    cls_top = getattr(ft, kind, None)
    if cls_top is not None and callable(cls_top):
        try:
            return cls_top(left=l, top=t, right=r, bottom=b)
        except Exception:
            try:
                return cls_top(l, t, r, b)
            except Exception:
                pass
    mod = getattr(ft, kind.lower(), None)
    if mod is not None and hasattr(mod, "only"):
        try:
            return mod.only(left=l, top=t, right=r, bottom=b)
        except Exception:
            pass
    if mod is not None and hasattr(mod, kind):
        try:
            cls_mod = getattr(mod, kind)
            return cls_mod(left=l, top=t, right=r, bottom=b)
        except Exception:
            pass
    return {"left": l, "top": t, "right": r, "bottom": b}


def pad(l=0, t=0, r=0, b=0):
    return _mk_inset("Padding", l, t, r, b)


def padv(h=0, v=0):
    return _mk_inset("Padding", h, v, h, v)


def marg(l=0, t=0, r=0, b=0):
    return _mk_inset("Margin", l, t, r, b)


# Rellenamos los módulos por si algo externo llama a la API vieja
try:
    if not hasattr(ft.padding, "only"):
        ft.padding.only = lambda left=0, top=0, right=0, bottom=0: pad(left, top, right, bottom)
    if not hasattr(ft.padding, "all"):
        ft.padding.all = lambda n: pad(n, n, n, n)
    if not hasattr(ft.padding, "symmetric"):
        ft.padding.symmetric = lambda horizontal=0, vertical=0: padv(horizontal, vertical)
except Exception:
    pass
try:
    if not hasattr(ft.margin, "only"):
        ft.margin.only = lambda left=0, top=0, right=0, bottom=0: marg(left, top, right, bottom)
    if not hasattr(ft.margin, "all"):
        ft.margin.all = lambda n: marg(n, n, n, n)
    if not hasattr(ft.margin, "symmetric"):
        ft.margin.symmetric = lambda horizontal=0, vertical=0: marg(horizontal, vertical, horizontal, vertical)
except Exception:
    pass


# =========================================================================
#  🩹 SHIM DE ALIGNMENT
#  Flet nuevo expone la clase ft.Alignment(x, y) pero elimina las
#  constantes ft.alignment.center / top_left / etc. Las repoblamos.
#  Ejes: x, y en el rango [-1, 1]. Centro = (0, 0).
# =========================================================================
def _mk_align(x, y):
    cls = getattr(ft, "Alignment", None)
    if cls is not None:
        try:
            return cls(x, y)
        except Exception:
            try:
                return cls(x=x, y=y)
            except Exception:
                pass
    return None


_ALIGN_CONSTANTS = {
    "top_left":      (-1.0, -1.0),
    "top_center":    (0.0, -1.0),
    "top_right":     (1.0, -1.0),
    "center_left":   (-1.0, 0.0),
    "center":        (0.0, 0.0),
    "center_right":  (1.0, 0.0),
    "bottom_left":   (-1.0, 1.0),
    "bottom_center": (0.0, 1.0),
    "bottom_right":  (1.0, 1.0),
}
try:
    _align_mod = getattr(ft, "alignment", None)
    if _align_mod is not None:
        for _name, (_x, _y) in _ALIGN_CONSTANTS.items():
            if not hasattr(_align_mod, _name):
                _val = _mk_align(_x, _y)
                if _val is not None:
                    setattr(_align_mod, _name, _val)
except Exception:
    pass


# =========================================================================
#  🩹 SHIM DE ENUMS RENOMBRADOS
#  Flet nuevo renombró varios enums. Creamos alias hacia el nombre viejo
#  usado en este archivo si el atributo no existe.  {viejo: [nuevos...]}
# =========================================================================
_ENUM_ALIASES = {
    "ImageFit":           ["BoxFit"],
    "ImageRepeat":        ["ImageRepeat"],
    "MainAxisAlignment":  ["MainAxisAlignment"],
    "CrossAxisAlignment": ["CrossAxisAlignment"],
    "ClipBehavior":       ["ClipBehavior", "Clip"],
    "ScrollMode":         ["ScrollMode"],
    "FontWeight":         ["FontWeight"],
    "TextAlign":          ["TextAlign"],
}
for _old, _new_names in _ENUM_ALIASES.items():
    if not hasattr(ft, _old):
        for _new in _new_names:
            _cand = getattr(ft, _new, None)
            if _cand is not None:
                try:
                    setattr(ft, _old, _cand)
                except Exception:
                    pass
                break


def side(width=1, color="#000000"):
    """Devuelve un BorderSide compatible con cualquier Flet."""
    cls = getattr(ft, "BorderSide", None)
    if cls is not None:
        try:
            return cls(width=width, color=color)
        except Exception:
            try:
                return cls(width, color)
            except Exception:
                pass
    mod = getattr(ft, "border", None)
    if mod is not None and hasattr(mod, "BorderSide"):
        try:
            return mod.BorderSide(width, color)
        except Exception:
            pass
    return None


def bord(l=None, t=None, r=None, b=None):
    """ft.Border(...) en API nueva, ft.border.only(...) en API vieja."""
    cls_top = getattr(ft, "Border", None)
    if cls_top is not None:
        try:
            return cls_top(left=l, top=t, right=r, bottom=b)
        except Exception:
            pass
    mod = getattr(ft, "border", None)
    if mod is not None and hasattr(mod, "only"):
        try:
            return mod.only(left=l, top=t, right=r, bottom=b)
        except Exception:
            pass
    return None


def bord_all(width=1, color="#000000"):
    """Borde en los cuatro lados."""
    mod = getattr(ft, "border", None)
    if mod is not None and hasattr(mod, "all"):
        try:
            return mod.all(width, color)
        except Exception:
            pass
    cls_top = getattr(ft, "Border", None)
    if cls_top is not None and hasattr(cls_top, "all"):
        try:
            return cls_top.all(width, color)
        except Exception:
            pass
    s = side(width, color)
    if s is None:
        return None
    return bord(s, s, s, s)


# =========================================================================
#  🔧 PROXY DE ICONOS
# =========================================================================
class _IconsProxy:
    _ALIASES = {
        "MOVIE_OUTLINED":         ["MOVIE", "LOCAL_MOVIES", "VIDEOCAM"],
        "TV_OUTLINED":            ["TV", "LIVE_TV"],
        "AUTO_AWESOME_OUTLINED":  ["AUTO_AWESOME", "STAR", "STAR_OUTLINE"],
        "ARTICLE_OUTLINED":       ["ARTICLE", "DESCRIPTION", "DESCRIPTION_OUTLINED"],
        "GRID_VIEW_OUTLINED":     ["GRID_VIEW", "APPS", "VIEW_MODULE"],
        "PLAY_CIRCLE_OUTLINE":    ["PLAY_CIRCLE", "PLAY_CIRCLE_FILLED", "PLAY_CIRCLE_OUTLINED"],
        "MOVIE_FILTER_OUTLINED":  ["MOVIE_FILTER", "THEATERS"],
        "TRENDING_UP":            ["TRENDING_UP", "SHOW_CHART"],
        "ACCESS_TIME":            ["ACCESS_TIME", "SCHEDULE", "HISTORY"],
        "WIFI_OFF":               ["WIFI_OFF", "SIGNAL_WIFI_OFF", "WIFI"],
        "NOTIFICATIONS_NONE":     ["NOTIFICATIONS_NONE", "NOTIFICATIONS", "NOTIFICATIONS_OUTLINED"],
        "CALENDAR_TODAY":         ["CALENDAR_TODAY", "DATE_RANGE", "CALENDAR_MONTH"],
        "LAYERS_OUTLINED":        ["LAYERS", "LAYERS_OUTLINED"],
        "DNS_OUTLINED":           ["DNS", "CLOUD", "STORAGE"],
        "SHARE_OUTLINED":         ["SHARE", "SHARE_OUTLINED", "IOS_SHARE"],
        "BOOKMARK_OUTLINE":       ["BOOKMARK_BORDER", "BOOKMARK_OUTLINE", "BOOKMARK"],
        "HOME_OUTLINED":          ["HOME", "HOME_OUTLINED", "HOUSE"],
        "EXPLORE_OUTLINED":       ["EXPLORE", "EXPLORE_OUTLINED", "TRAVEL_EXPLORE"],
        "SETTINGS_OUTLINED":      ["SETTINGS", "SETTINGS_OUTLINED", "TUNE"],
        "PALETTE_OUTLINED":       ["PALETTE", "PALETTE_OUTLINED", "COLOR_LENS"],
        "INFO_OUTLINE":           ["INFO", "INFO_OUTLINE", "INFO_OUTLINED"],
        "SEARCH_OFF":             ["SEARCH_OFF", "SEARCH"],
        "LOCAL_FIRE_DEPARTMENT":  ["LOCAL_FIRE_DEPARTMENT", "WHATSHOT", "FIREPLACE"],
        "KEYBOARD_ARROW_UP":      ["KEYBOARD_ARROW_UP", "ARROW_UPWARD", "EXPAND_LESS"],
        "KEYBOARD_ARROW_DOWN":    ["KEYBOARD_ARROW_DOWN", "ARROW_DOWNWARD", "EXPAND_MORE"],
        "ARROW_BACK":             ["ARROW_BACK", "ARROW_LEFT", "CHEVRON_LEFT"],
        "CHEVRON_RIGHT":          ["CHEVRON_RIGHT", "ARROW_FORWARD", "NAVIGATE_NEXT"],
        "PLAY_ARROW":             ["PLAY_ARROW", "PLAY_ARROW_OUTLINED", "PLAY"],
        "STAR":                   ["STAR", "STAR_RATE"],
        "SEARCH":                 ["SEARCH"],
        "PERSON":                 ["PERSON", "ACCOUNT_CIRCLE"],
        "LOGOUT":                 ["LOGOUT", "EXIT_TO_APP"],
        "RSS_FEED":               ["RSS_FEED", "RSS"],
        "LANGUAGE":               ["LANGUAGE", "TRANSLATE"],
        "BOOKMARK":               ["BOOKMARK", "BOOKMARK_OUTLINE"],
        "BOOKMARK_ADDED":         ["BOOKMARK_ADDED", "BOOKMARK", "CHECK"],
        "MOVIE_FILTER":           ["MOVIE_FILTER", "THEATERS"],
    }

    def __init__(self):
        self._new = getattr(ft, "Icons", None)
        self._old = getattr(ft, "icons", None)
        self._cache = {}

    def __getattr__(self, name):
        if name in self._cache:
            return self._cache[name]
        for api in (self._new, self._old):
            if api is not None and hasattr(api, name):
                val = getattr(api, name)
                self._cache[name] = val
                return val
        for alias in self._ALIASES.get(name, []):
            for api in (self._new, self._old):
                if api is not None and hasattr(api, alias):
                    val = getattr(api, alias)
                    self._cache[name] = val
                    return val
        for api in (self._new, self._old):
            if api is not None and hasattr(api, "CIRCLE"):
                val = getattr(api, "CIRCLE")
                self._cache[name] = val
                print(f"[Fotograma] Icono '{name}' no existe, usando CIRCLE.")
                return val
        raise AttributeError(f"Icono '{name}' no disponible")


icons = _IconsProxy()


# ----------------------------- Paleta ------------------------------------
ACCENT      = "#fd6500"
ACCENT_DARK = "#b3862c"
ACCENT_SOFT = "#3a2a10"
BG          = "#0a0a0b"
BG_RAISED   = "#131315"
CARD        = "#17171a"
CARD_BORDER = "#232326"
TEXT        = "#f2f1ee"
MUTED       = "#8d8d95"
MUTED_SOFT  = "#56565c"

RADIUS_LG = 22
RADIUS_MD = 14
RADIUS_SM = 10

TYPE_META = {
    "pelicula": ("Película", icons.MOVIE_OUTLINED),
    "serie":    ("Serie",    icons.TV_OUTLINED),
    "anime":    ("Anime",    icons.AUTO_AWESOME_OUTLINED),
    "blog":     ("Artículo", icons.ARTICLE_OUTLINED),
}
MAIN_TABS = [
    ("all",      "Todos",     icons.GRID_VIEW_OUTLINED),
    ("pelicula", "Películas", icons.MOVIE_OUTLINED),
    ("serie",    "Series",    icons.TV_OUTLINED),
    ("anime",    "Anime",     icons.AUTO_AWESOME_OUTLINED),
]


# =========================================================================
#  MODELOS
# =========================================================================
@dataclass
class Server:
    name: str
    embed_url: str
    internal_name: Optional[str] = None

    @classmethod
    def from_json(cls, j):
        return cls(
            name=str(j.get("name") or j.get("internalName") or "Servidor"),
            embed_url=str(j.get("embedUrl") or ""),
            internal_name=j.get("internalName"),
        )


@dataclass
class Episode:
    number: int
    title: str
    synopsis: str
    still_url: Optional[str]
    duration: Optional[str]
    servers: dict

    @classmethod
    def from_json(cls, j):
        return cls(
            number=int(j.get("episodeNumber") or 0),
            title=str(j.get("title") or ""),
            synopsis=str(j.get("synopsis") or ""),
            still_url=j.get("stillUrl"),
            duration=j.get("duration"),
            servers=_parse_servers(j.get("serversByLanguage") or {}),
        )


@dataclass
class Season:
    number: int
    episodes: list

    @classmethod
    def from_json(cls, j):
        return cls(
            number=int(j.get("seasonNumber") or 0),
            episodes=[Episode.from_json(e) for e in (j.get("episodes") or [])],
        )


def _parse_servers(raw):
    out = {}
    for lang, arr in (raw or {}).items():
        if isinstance(arr, list):
            out[str(lang)] = [Server.from_json(s) for s in arr if isinstance(s, dict)]
    return out


@dataclass
class Post:
    id: str
    link: str
    cats: list
    published: datetime
    updated: datetime
    author: str
    comments: int
    structured: bool
    kind: str
    type: str
    title: str
    year: Optional[int]
    rating: Optional[float]
    duration: str
    img: str
    background_url: str
    logo_url: str
    synopsis: str
    genres: list
    default_lang: str
    servers_by_language: dict
    seasons: list
    content: Optional[str] = None
    read_mins: Optional[int] = None
    slug: str = ""

    @staticmethod
    def _extract_payload(raw):
        if not raw:
            return None
        m = re.search(r"base64--([A-Za-z0-9+/=]+)", raw)
        if not m:
            return None
        try:
            decoded = base64.b64decode(m.group(1)).decode("utf-8", errors="replace")
            return json.loads(decoded)
        except Exception as e:
            print("payload base64-- inválido:", e)
            return None

    @staticmethod
    def _detect_type_from_cats(cats):
        j = " ".join(cats).lower()
        if "anime" in j:
            return "anime"
        if "serie" in j or "show" in j:
            return "serie"
        if any(k in j for k in ("pelic", "pelí", "movie", "film")):
            return "pelicula"
        return "blog"

    @classmethod
    def from_entry(cls, e, index):
        links = e.get("link") or []
        link = "#"
        for l in links:
            if l.get("rel") == "alternate":
                link = l.get("href", "#")
                break
        cats = [c.get("term", "") for c in (e.get("category") or [])]
        cats = [c for c in cats if c]
        pid = str((e.get("id") or {}).get("$t") or index)
        published = _parse_dt((e.get("published") or {}).get("$t")) or datetime.now()
        updated = _parse_dt((e.get("updated") or {}).get("$t")) or published
        author = "Fotograma"
        try:
            author = e["author"][0]["name"]["$t"]
        except Exception:
            pass
        comments = 0
        try:
            comments = int((e.get("thr$total") or {}).get("$t") or 0)
        except Exception:
            pass
        raw = (e.get("content") or {}).get("$t") or (e.get("summary") or {}).get("$t") or ""
        payload = cls._extract_payload(raw)

        if payload:
            is_anime = any("anime" in c.lower() for c in cats)
            kind = str(payload.get("type") or "movie")
            ptype = "anime" if is_anime else (
                "pelicula" if kind == "movie"
                else "serie" if kind == "show"
                else "blog"
            )
            return cls(
                id=pid, link=link, cats=cats,
                published=published, updated=updated,
                author=author, comments=comments,
                structured=True, kind=kind, type=ptype,
                title=str(payload.get("title") or "(sin título)"),
                year=payload.get("year") if isinstance(payload.get("year"), int) else None,
                rating=float(payload["rating"]) if isinstance(payload.get("rating"), (int, float)) else None,
                duration=str(payload.get("duration") or ""),
                img=str(payload.get("posterUrl") or ""),
                background_url=str(payload.get("backgroundUrl") or payload.get("posterUrl") or ""),
                logo_url=str(payload.get("logoUrl") or ""),
                synopsis=str(payload.get("synopsis") or ""),
                genres=[g.strip() for g in str(payload.get("genres") or "").split(",") if g.strip()],
                default_lang=str(payload.get("defaultLang") or ""),
                servers_by_language=_parse_servers(payload.get("serversByLanguage") or {}),
                seasons=[Season.from_json(s) for s in (payload.get("seasons") or [])],
            )

        thumb = ""
        try:
            thumb = e["media$thumbnail"]["$t"] or ""
        except Exception:
            pass
        img = re.sub(r"s\d+(-c)?", "s800", thumb) if thumb else ""
        words = len(re.sub(r"<[^>]+>", " ", raw).split())
        return cls(
            id=pid, link=link, cats=cats,
            published=published, updated=updated,
            author=author, comments=comments,
            structured=False, kind="blog",
            type=cls._detect_type_from_cats(cats),
            title=str((e.get("title") or {}).get("$t") or ""),
            year=None, rating=None, duration="",
            img=img, background_url=img, logo_url="",
            synopsis="", genres=[], default_lang="",
            servers_by_language={}, seasons=[],
            content=raw,
            read_mins=max(1, round(words / 200)),
        )


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


# =========================================================================
#  UTILIDADES
# =========================================================================
def slugify(s):
    s = s.lower()
    trans = str.maketrans("áéíóúñüàèìòù", "aeiounuaeiou")
    s = s.translate(trans)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s[:60] or "entrada")


def short_hash(s):
    h = 0
    for ch in s:
        h = ((h * 31) + ord(ch)) & 0xFFFFFFFF
    return format(h, "06x")[:6]


def assign_slugs(posts):
    seen = set()
    for p in posts:
        base = slugify(p.title)
        slug = f"{base}-{short_hash(p.id)}"
        n = 2
        while slug in seen:
            slug = f"{base}-{short_hash(p.id)}-{n}"
            n += 1
        seen.add(slug)
        p.slug = slug


def fmt_date(d):
    meses = ["ene", "feb", "mar", "abr", "may", "jun",
             "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"{d.day} {meses[d.month - 1]} {d.year}"


# =========================================================================
#  RESOLVER DE VIDHIDE
# =========================================================================
def _to_base(n, base):
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "0"
    out = []
    while n > 0:
        out.append(digits[n % base])
        n //= base
    return "".join(reversed(out))


def _edwards_unpack(expr):
    m = re.search(
        r"\(\s*['\"](.*?)['\"]\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*['\"](.*?)['\"]\.split\(['\"]\|['\"]\)\s*\)\s*$",
        expr, re.DOTALL,
    )
    if not m:
        return None
    payload, a, c, k_str = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
    k = k_str.split("|")
    p = payload
    for i in range(c - 1, -1, -1):
        if i < len(k) and k[i]:
            token = _to_base(i, a)
            p = re.sub(r"\b" + re.escape(token) + r"\b", k[i], p)
    return p


def _unpack_eval(html):
    idx = html.find("eval(function(p,a,c,k,e,d)")
    if idx == -1:
        return None
    rest = html[idx:]
    m = re.search(r"\.split\(['\"]\|['\"]\)\)\)", rest)
    if not m:
        return None
    code = rest[: m.end()]
    inner = code[5:-1]
    try:
        return _edwards_unpack(inner)
    except Exception as e:
        print("unpack falló:", e)
        return None


def _absolutize(url, base):
    if url.startswith(("http://", "https://")):
        return url
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        p = urllib.parse.urlparse(base)
        return f"{p.scheme}://{p.netloc}{url}"
    return urllib.parse.urljoin(base, url)


def resolve_vidhide(embed_url, timeout=20):
    req = urllib.request.Request(
        embed_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36"
            ),
            "Referer": embed_url,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        html = r.read().decode("utf-8", errors="replace")
    source = _unpack_eval(html) or html

    m = re.search(r"(?:var\s+)?links\s*=\s*(\{[\s\S]*?\})\s*[;,]", source)
    if m:
        raw = m.group(1)
        for key in ("hls2", "hls3", "hls4", "hls", "mp4", "direct"):
            mm = re.search(rf'["\']?{key}["\']?\s*:\s*["\']([^"\']+)["\']', raw)
            if mm:
                return _absolutize(mm.group(1), embed_url)
    for key in ("hls2", "hls3", "hls4"):
        mm = re.search(rf'["\']?{key}["\']?\s*[:=]\s*["\']([^"\']+)["\']', source, re.I)
        if mm:
            return _absolutize(mm.group(1), embed_url)
    mm = re.search(r'file\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', source, re.I)
    if mm:
        return _absolutize(mm.group(1), embed_url)
    mm = re.search(r'["\']([^"\']+\.m3u8[^"\']*)["\']', source)
    if mm:
        return _absolutize(mm.group(1), embed_url)
    return None


# =========================================================================
#  FEED
# =========================================================================
class FeedService:
    PAGE_SIZE = 150
    MAX_TOTAL = 3000

    @classmethod
    def load_all(cls):
        collected = []
        start = 1
        while True:
            url = (
                f"{BLOG_URL}/feeds/posts/default"
                f"?alt=json&max-results={cls.PAGE_SIZE}&start-index={start}"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            try:
                with urllib.request.urlopen(req, timeout=25) as r:
                    data = json.loads(r.read().decode("utf-8", errors="replace"))
            except Exception as e:
                print("feed error:", e)
                break
            entries = ((data.get("feed") or {}).get("entry") or [])
            if not entries:
                break
            for i, e in enumerate(entries):
                collected.append(Post.from_entry(e, start + i))
            if len(entries) < cls.PAGE_SIZE:
                break
            start += cls.PAGE_SIZE
            if start > cls.MAX_TOTAL:
                break
        assign_slugs(collected)
        return collected


# =========================================================================
#  ESTADO
# =========================================================================
class State:
    posts = []
    saved = set()
    viewed = set()
    loading = True
    error = None

    @classmethod
    def by_id(cls, pid):
        return next((p for p in cls.posts if p.id == pid), None)

    @classmethod
    def by_type(cls, t):
        return [p for p in cls.posts if p.type == t]

    @classmethod
    def sorted_date(cls, arr):
        return sorted(arr, key=lambda p: p.published, reverse=True)

    @classmethod
    def sorted_updated(cls, arr):
        return sorted(arr, key=lambda p: p.updated, reverse=True)

    @classmethod
    def sorted_popularity(cls, arr):
        return sorted(arr, key=lambda p: (p.rating or 0) * 10 + p.comments, reverse=True)


# =========================================================================
#  WIDGETS COMUNES
# =========================================================================
def section_title(text, icon, count=""):
    right = ft.Text(count, size=12, color=MUTED) if count else ft.Container()
    return ft.Container(
        padding=pad(18, 22, 18, 12),
        content=ft.Row(
            [
                ft.Icon(icon, color=ACCENT, size=18),
                ft.Container(width=9),
                ft.Text(text, size=15, weight=ft.FontWeight.W_700, color=TEXT),
                ft.Container(expand=True),
                right,
            ],
            spacing=0,
        ),
    )


def rating_chip(rating):
    if rating is None:
        return ft.Container(width=0, height=0)
    return ft.Container(
        padding=padv(6, 3),
        bgcolor="#c0000000",
        border_radius=6,
        content=ft.Row(
            [
                ft.Icon(icons.STAR, size=10, color=ACCENT),
                ft.Container(width=3),
                ft.Text(f"{rating:.1f}", size=10, weight=ft.FontWeight.W_700, color=ACCENT),
            ],
            spacing=0, tight=True,
        ),
    )


def type_chip(ptype):
    label, icon = TYPE_META[ptype]
    return ft.Container(
        padding=padv(6, 3),
        bgcolor="#c0000000",
        border_radius=6,
        content=ft.Row(
            [
                ft.Icon(icon, size=10, color=ACCENT),
                ft.Container(width=3),
                ft.Text(label, size=10, weight=ft.FontWeight.W_600, color=ACCENT),
            ],
            spacing=0, tight=True,
        ),
    )


def poster(url, width=None, height=None, radius=RADIUS_SM):
    if not url:
        return ft.Container(
            width=width, height=height,
            bgcolor=CARD, border_radius=radius,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
    return ft.Container(
        width=width, height=height,
        border_radius=radius,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        bgcolor=CARD_BORDER,
        content=ft.Image(src=url, fit=ft.ImageFit.COVER),
    )


def fill_gradient(colors, begin, end, stops=None):
    return ft.Container(
        left=0, top=0, right=0, bottom=0,
        gradient=ft.LinearGradient(begin=begin, end=end, colors=colors, stops=stops),
    )


# =========================================================================
#  VISTA: INICIO
# =========================================================================
class HomeView(ft.Container):
    def __init__(self, app):
        super().__init__(expand=True, bgcolor=BG)
        self.app = app
        self.content = self._build()

    def _build(self):
        if State.loading:
            return ft.Container(expand=True, alignment=ft.alignment.center,
                                content=ft.ProgressRing(color=ACCENT))
        if State.error:
            return ft.Container(
                expand=True, alignment=ft.alignment.center,
                padding=pad(40, 40, 40, 40),
                content=ft.Column(
                    [
                        ft.Icon(icons.WIFI_OFF, size=40, color=MUTED_SOFT),
                        ft.Container(height=12),
                        ft.Text("No se pudo cargar el feed.",
                                color=MUTED, size=14, text_align=ft.TextAlign.CENTER),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0,
                ),
            )

        items = State.sorted_date(State.posts)[:6]
        rows = [
            ("Últimos estrenos", icons.MOVIE_OUTLINED,
             State.sorted_date(State.by_type("pelicula"))[:12]),
            ("Últimas series", icons.TV_OUTLINED,
             State.sorted_date(State.by_type("serie"))[:12]),
            ("Sigue viendo", icons.PLAY_CIRCLE_OUTLINE,
             [p for p in State.posts if p.id in State.viewed][:12]),
            ("Películas", icons.MOVIE_FILTER_OUTLINED,
             State.sorted_date(State.by_type("pelicula"))[:12]),
            ("Lo más popular", icons.TRENDING_UP,
             State.sorted_popularity(State.posts)[:12]),
            ("Anime", icons.AUTO_AWESOME_OUTLINED,
             State.sorted_date(State.by_type("anime"))[:12]),
            ("Recién agregado", icons.ACCESS_TIME,
             State.sorted_updated(State.posts)[:12]),
        ]

        children = [self._header()]
        if items:
            children.append(section_title("Recomendados para ti", icons.LOCAL_FIRE_DEPARTMENT))
            children.append(self._slider(items))
        for title, icon, arr in rows:
            children.append(section_title(title, icon))
            if arr:
                children.append(self._row(arr))
            else:
                children.append(ft.Container(
                    padding=pad(18, 0, 18, 8),
                    content=ft.Text("Todavía no hay contenido.",
                                    color=MUTED_SOFT, size=13),
                ))
        children.append(ft.Container(height=90))
        return ft.ListView(controls=children, expand=True, spacing=0, padding=0)

    def _header(self):
        return ft.Container(
            padding=pad(18, 16, 18, 16),
            border=bord(b=side(1, CARD_BORDER)),
            content=ft.Row(
                [
                    ft.Container(
                        width=38, height=38, border_radius=11,
                        gradient=ft.LinearGradient(
                            begin=ft.alignment.top_left,
                            end=ft.alignment.bottom_right,
                            colors=[ACCENT, ACCENT_DARK],
                        ),
                        alignment=ft.alignment.center,
                        content=ft.Icon(icons.MOVIE_FILTER, color="#000", size=20),
                    ),
                    ft.Container(width=10),
                    ft.Text("FOTOGRAMA", size=22, weight=ft.FontWeight.BOLD, color=TEXT),
                    ft.Container(expand=True),
                    self._icon_btn(icons.SEARCH, lambda e: self.app.switch_tab(2)),
                    ft.Container(width=8),
                    self._icon_btn(icons.NOTIFICATIONS_NONE, lambda e: None),
                ],
                spacing=0,
            ),
        )

    def _icon_btn(self, icon, on_click):
        return ft.Container(
            width=38, height=38, border_radius=30,
            bgcolor=CARD,
            border=bord_all(1, CARD_BORDER),
            alignment=ft.alignment.center,
            on_click=on_click,
            content=ft.Icon(icon, size=18, color=TEXT),
        )

    def _slider(self, items):
        page_w = self.app.page.width or 400
        card_w = int(page_w * 0.78)
        return ft.Container(
            height=238, padding=pad(18, 4, 18, 6),
            content=ft.Row(
                controls=[self._slide(p, card_w) for p in items],
                scroll=ft.ScrollMode.ADAPTIVE, spacing=12, tight=True,
            ),
        )

    def _slide(self, p, width):
        bg = p.background_url or p.img
        body_children = [
            ft.Container(
                padding=padv(10, 4), bgcolor=ACCENT, border_radius=7,
                content=ft.Text(TYPE_META[p.type][0], size=10,
                                weight=ft.FontWeight.W_700, color="#000"),
            ),
            ft.Container(height=9),
        ]
        if p.logo_url:
            body_children.append(
                ft.Container(
                    alignment=ft.alignment.bottom_left,
                    content=ft.Image(src=p.logo_url, height=50,
                                     fit=ft.ImageFit.CONTAIN),
                )
            )
        else:
            body_children.append(
                ft.Text(p.title, size=22, max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        weight=ft.FontWeight.BOLD, color="#fff")
            )
        stack_children = [
            poster(bg, width=width, height=230, radius=RADIUS_LG),
            fill_gradient(
                colors=["#e6000000", "#00000000"],
                begin=ft.alignment.bottom_center,
                end=ft.alignment.top_center,
                stops=[0.05, 0.7],
            ),
        ]
        if p.rating is not None:
            stack_children.append(ft.Container(top=12, right=12, content=rating_chip(p.rating)))
        stack_children.append(
            ft.Container(
                left=16, right=16, bottom=16,
                content=ft.Column(body_children, spacing=0, tight=True),
            )
        )
        return ft.Container(
            width=width, height=230, border_radius=RADIUS_LG,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            on_click=lambda e: self.app.open_detail(p.id),
            content=ft.Stack(stack_children, width=width, height=230),
        )

    def _row(self, items):
        return ft.Container(
            height=222, padding=pad(18, 2, 18, 6),
            content=ft.Row(
                controls=[self._row_card(p) for p in items],
                scroll=ft.ScrollMode.ADAPTIVE, spacing=11, tight=True,
            ),
        )

    def _row_card(self, p):
        stack_children = [
            poster(p.img, width=118, height=177, radius=RADIUS_SM),
            ft.Container(top=6, left=6, content=type_chip(p.type)),
        ]
        if p.rating is not None:
            stack_children.append(ft.Container(bottom=6, right=6, content=rating_chip(p.rating)))
        return ft.Container(
            width=118,
            on_click=lambda e: self.app.open_detail(p.id),
            content=ft.Column(
                [
                    ft.Stack(stack_children, width=118, height=177),
                    ft.Container(height=6),
                    ft.Text(p.title, size=12, weight=ft.FontWeight.W_600,
                            color=TEXT, max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS),
                ],
                spacing=0, tight=True,
            ),
        )


# =========================================================================
#  VISTA: EXPLORAR
# =========================================================================
class ExploreView(ft.Container):
    def __init__(self, app):
        super().__init__(expand=True, bgcolor=BG)
        self.app = app
        self.category = "all"
        self.query = ""
        self.grid_holder = ft.Container(expand=True)
        self.count_text = ft.Text("", size=12, color=MUTED)
        self.search_field = ft.TextField(
            hint_text="Buscar películas, series, anime...",
            border=ft.InputBorder.NONE,
            bgcolor="transparent", color=TEXT, text_size=14,
            on_change=self._on_search, expand=True,
            content_padding=pad(6, 6, 6, 6),
        )
        self.chips_row = ft.Row(scroll=ft.ScrollMode.ADAPTIVE, spacing=8)
        self._build_ui()

    def _build_ui(self):
        self.content = ft.Column(
            [
                ft.Container(
                    padding=pad(18, 16, 18, 12),
                    content=ft.Container(
                        bgcolor=CARD,
                        border=bord_all(1, CARD_BORDER),
                        border_radius=RADIUS_MD,
                        padding=padv(10, 6),
                        content=ft.Row(
                            [
                                ft.Icon(icons.SEARCH, color=MUTED, size=18),
                                ft.Container(width=8),
                                self.search_field,
                            ],
                            spacing=0,
                        ),
                    ),
                ),
                ft.Container(padding=pad(18, 0, 18, 14), content=self.chips_row),
                ft.Container(
                    padding=pad(18, 22, 18, 12),
                    content=ft.Row(
                        [
                            ft.Icon(icons.GRID_VIEW_OUTLINED, color=ACCENT, size=18),
                            ft.Container(width=9),
                            ft.Text("Todo el contenido", size=15,
                                    weight=ft.FontWeight.W_700, color=TEXT),
                            ft.Container(expand=True),
                            self.count_text,
                        ],
                        spacing=0,
                    ),
                ),
                self.grid_holder,
            ],
            spacing=0, expand=True,
        )
        self._build_chips()
        self._refresh_grid()

    def _build_chips(self):
        self.chips_row.controls.clear()
        for cid, label, icon in MAIN_TABS:
            active = self.category == cid
            self.chips_row.controls.append(
                ft.Container(
                    padding=padv(15, 8),
                    bgcolor=ACCENT_SOFT if active else CARD,
                    border=bord_all(1, ACCENT if active else CARD_BORDER),
                    border_radius=30,
                    on_click=lambda e, c=cid: self._set_cat(c),
                    content=ft.Row(
                        [
                            ft.Icon(icon, size=14, color=ACCENT if active else MUTED),
                            ft.Container(width=6),
                            ft.Text(label, size=13,
                                    color=ACCENT if active else MUTED,
                                    weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_400),
                        ],
                        tight=True, spacing=0,
                    ),
                )
            )

    def _set_cat(self, cid):
        self.category = cid
        self._build_chips()
        self._refresh_grid()
        try: self.update()
        except Exception: pass

    def _on_search(self, e):
        self.query = (self.search_field.value or "").strip().lower()
        self._refresh_grid()
        try:
            self.grid_holder.update()
            self.count_text.update()
        except Exception:
            pass

    def _filtered(self):
        out = []
        for p in State.posts:
            if self.category != "all" and p.type != self.category:
                continue
            if self.query and self.query not in p.title.lower():
                continue
            out.append(p)
        return out

    def _refresh_grid(self):
        items = self._filtered()
        self.count_text.value = (
            f"{len(items)} resultado{'s' if len(items) != 1 else ''}"
            if items else ""
        )
        if not items:
            self.grid_holder.content = ft.Container(
                padding=pad(40, 40, 40, 40),
                alignment=ft.alignment.center,
                content=ft.Column(
                    [
                        ft.Icon(icons.SEARCH_OFF, size=40, color=MUTED_SOFT),
                        ft.Container(height=12),
                        ft.Text("No encontramos nada por aquí.\nPrueba con otra categoría o búsqueda.",
                                color=MUTED, size=13, text_align=ft.TextAlign.CENTER),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0,
                ),
            )
            return
        self.grid_holder.content = ft.GridView(
            expand=True, runs_count=2,
            spacing=14, run_spacing=14,
            padding=pad(18, 0, 18, 20),
            controls=[self._card(p) for p in items],
        )

    def _card(self, p):
        saved = p.id in State.saved
        stack_children = [
            poster(p.img, height=240),
            ft.Container(top=8, left=8, content=type_chip(p.type)),
            ft.Container(
                top=8, right=8,
                on_click=lambda e: self._toggle_save(p.id),
                content=ft.Container(
                    width=28, height=28, bgcolor="#c0000000",
                    border_radius=30, alignment=ft.alignment.center,
                    content=ft.Icon(
                        icons.BOOKMARK if not saved else icons.BOOKMARK_ADDED,
                        size=14,
                        color=ACCENT if saved else "#fff",
                    ),
                ),
            ),
        ]
        if p.rating is not None:
            stack_children.append(ft.Container(bottom=8, left=8, content=rating_chip(p.rating)))
        return ft.Container(
            bgcolor=CARD,
            border=bord_all(1, CARD_BORDER),
            border_radius=RADIUS_MD,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            on_click=lambda e: self.app.open_detail(p.id),
            content=ft.Column(
                [
                    ft.Stack(stack_children, height=240),
                    ft.Container(
                        padding=pad(11, 10, 11, 12),
                        content=ft.Column(
                            [
                                ft.Text(p.title, size=13, weight=ft.FontWeight.W_600,
                                        max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                                        color=TEXT),
                                ft.Container(height=6),
                                ft.Row(
                                    [
                                        ft.Icon(icons.CALENDAR_TODAY, size=11, color=MUTED),
                                        ft.Container(width=5),
                                        ft.Text(p.year and str(p.year) or fmt_date(p.published),
                                                size=11, color=MUTED),
                                    ],
                                    tight=True, spacing=0,
                                ),
                            ],
                            spacing=0, tight=True,
                        ),
                    ),
                ],
                spacing=0, tight=True,
            ),
        )

    def _toggle_save(self, pid):
        if pid in State.saved:
            State.saved.remove(pid)
        else:
            State.saved.add(pid)
        self._refresh_grid()
        try: self.grid_holder.update()
        except Exception: pass


# =========================================================================
#  VISTA: MIS LISTAS
# =========================================================================
class ListsView(ft.Container):
    def __init__(self, app):
        super().__init__(expand=True, bgcolor=BG)
        self.app = app
        self.holder = ft.Container(expand=True)
        self.title_control = section_title("Mis listas", icons.BOOKMARK_OUTLINE,
                                           self._count_text())
        self._refresh()
        self.content = ft.Column([self.title_control, self.holder], spacing=0, expand=True)

    def _count_text(self):
        n = len(State.saved)
        return f"{n} guardado{'s' if n != 1 else ''}" if n else ""

    def _refresh(self):
        items = [p for p in State.posts if p.id in State.saved]
        if not items:
            self.holder.content = ft.Container(
                padding=pad(40, 40, 40, 40),
                alignment=ft.alignment.center,
                content=ft.Column(
                    [
                        ft.Icon(icons.BOOKMARK_OUTLINE, size=40, color=MUTED_SOFT),
                        ft.Container(height=12),
                        ft.Text("Aún no guardaste nada.\nToca el ícono de guardar en cualquier título.",
                                color=MUTED, size=13, text_align=ft.TextAlign.CENTER),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0,
                ),
            )
            return
        self.holder.content = ft.GridView(
            expand=True, runs_count=2, spacing=14, run_spacing=14,
            padding=pad(18, 0, 18, 20),
            controls=[self._card(p) for p in items],
        )

    def _card(self, p):
        stack_children = [
            poster(p.img, height=240),
            ft.Container(
                top=8, right=8,
                on_click=lambda e: self._toggle(p.id),
                content=ft.Container(
                    width=28, height=28, bgcolor="#c0000000",
                    border_radius=30, alignment=ft.alignment.center,
                    content=ft.Icon(icons.BOOKMARK_ADDED, size=14, color=ACCENT),
                ),
            ),
        ]
        if p.rating is not None:
            stack_children.append(ft.Container(bottom=8, left=8, content=rating_chip(p.rating)))
        return ft.Container(
            bgcolor=CARD,
            border=bord_all(1, CARD_BORDER),
            border_radius=RADIUS_MD,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            on_click=lambda e: self.app.open_detail(p.id),
            content=ft.Column(
                [
                    ft.Stack(stack_children, height=240),
                    ft.Container(
                        padding=pad(11, 10, 11, 12),
                        content=ft.Text(p.title, size=13, weight=ft.FontWeight.W_600,
                                        max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                                        color=TEXT),
                    ),
                ],
                spacing=0, tight=True,
            ),
        )

    def _toggle(self, pid):
        State.saved.discard(pid)
        self._refresh()
        try: self.update()
        except Exception: pass


# =========================================================================
#  VISTA: AJUSTES
# =========================================================================
class SettingsView(ft.Container):
    def __init__(self, app):
        super().__init__(expand=True, bgcolor=BG)
        self.app = app
        self.content = ft.ListView(
            [
                ft.Container(height=20),
                ft.Container(
                    padding=padv(18, 0),
                    content=ft.Row(
                        [
                            ft.Container(
                                width=60, height=60, border_radius=30,
                                gradient=ft.LinearGradient(
                                    begin=ft.alignment.top_left,
                                    end=ft.alignment.bottom_right,
                                    colors=[ACCENT, ACCENT_DARK],
                                ),
                                alignment=ft.alignment.center,
                                content=ft.Icon(icons.PERSON, size=26, color="#000"),
                            ),
                            ft.Container(width=14),
                            ft.Column(
                                [
                                    ft.Text("Invitado", size=16,
                                            weight=ft.FontWeight.W_600, color=TEXT),
                                    ft.Container(height=3),
                                    ft.Text("Explorando Fotograma", size=13, color=MUTED),
                                ],
                                spacing=0, tight=True,
                            ),
                        ],
                    ),
                ),
                ft.Container(height=24),
                self._label("Preferencias"),
                self._group([
                    self._item(icons.PALETTE_OUTLINED, "Color de acento",
                               "Se configura en el código"),
                    self._item(icons.NOTIFICATIONS_NONE, "Notificaciones",
                               "Nuevos estrenos y capítulos"),
                    self._item(icons.RSS_FEED, "Fuente de contenido",
                               BLOG_URL.replace("https://", "").replace("http://", "")),
                ]),
                ft.Container(height=10),
                self._label("Cuenta"),
                self._group([
                    self._item(icons.INFO_OUTLINE, "Acerca de Fotograma",
                               "Películas, series y anime"),
                    self._item(icons.LOGOUT, "Cerrar sesión", None),
                ]),
                ft.Container(height=90),
            ],
            spacing=0, expand=True,
        )

    def _label(self, text):
        return ft.Container(
            padding=pad(22, 10, 22, 8),
            content=ft.Text(text.upper(), size=11, color=MUTED_SOFT,
                            weight=ft.FontWeight.W_500),
        )

    def _group(self, items):
        return ft.Container(
            margin=marg(18, 0, 18, 0),
            bgcolor=CARD,
            border=bord_all(1, CARD_BORDER),
            border_radius=RADIUS_MD,
            content=ft.Column(items, spacing=0, tight=True),
        )

    def _item(self, icon, title, sub):
        children = [ft.Text(title, size=14, weight=ft.FontWeight.W_600, color=TEXT)]
        if sub:
            children.append(ft.Container(height=2))
            children.append(ft.Text(sub, size=12, color=MUTED,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS))
        return ft.Container(
            padding=padv(14, 13),
            border=bord(b=side(1, CARD_BORDER)),
            content=ft.Row(
                [
                    ft.Container(
                        width=32, height=32, bgcolor=ACCENT_SOFT,
                        border_radius=9, alignment=ft.alignment.center,
                        content=ft.Icon(icon, size=16, color=ACCENT),
                    ),
                    ft.Container(width=12),
                    ft.Column(children, spacing=0, tight=True, expand=True),
                    ft.Icon(icons.CHEVRON_RIGHT, size=16, color=MUTED_SOFT),
                ],
                spacing=0,
            ),
        )


# =========================================================================
#  VISTA: DETALLE
# =========================================================================
class DetailView(ft.Container):
    def __init__(self, app, post_id):
        super().__init__(expand=True, bgcolor=BG)
        self.app = app
        self.post = State.by_id(post_id)
        if self.post:
            State.viewed.add(post_id)
        self.season_index = 0
        self.selected_lang = None
        self.expanded_episode = None
        self.episode_langs = {}
        if not self.post:
            self.content = ft.Container(
                alignment=ft.alignment.center,
                content=ft.Text("Contenido no encontrado.", color=MUTED),
            )
            return
        self.content = self._build()

    def _build(self):
        p = self.post
        bg = p.background_url or p.img
        body = [
            ft.Container(
                padding=padv(11, 5), bgcolor=ACCENT_SOFT, border_radius=8,
                content=ft.Text(TYPE_META[p.type][0], size=11,
                                weight=ft.FontWeight.W_700, color=ACCENT),
            ),
            ft.Container(height=12),
        ]
        if not p.logo_url:
            body.append(ft.Text(p.title, size=28, weight=ft.FontWeight.BOLD, color=TEXT))
            body.append(ft.Container(height=10))
        body.append(self._meta_line())
        body.append(ft.Container(height=14))
        if p.genres:
            body.append(ft.Row(
                [ft.Container(
                    padding=padv(11, 5),
                    bgcolor=CARD, border=bord_all(1, CARD_BORDER), border_radius=30,
                    content=ft.Text(g, size=11, color=MUTED),
                ) for g in p.genres],
                wrap=True, spacing=7, run_spacing=7,
            ))
            body.append(ft.Container(height=18))
        body.append(self._actions())
        body.append(ft.Container(height=20))
        if p.structured:
            body.extend(self._structured_body())
        elif p.content:
            txt = re.sub(r"<[^>]+>", " ", p.content)
            body.append(ft.Text(txt, size=14, color="#cfced0"))

        hero_children = [
            poster(bg, height=250, radius=0),
            fill_gradient(
                colors=["#ff0a0a0b", "#00000000"],
                begin=ft.alignment.bottom_center,
                end=ft.alignment.top_center,
                stops=[0.0, 0.6],
            ),
        ]
        if p.logo_url:
            hero_children.append(
                ft.Container(
                    left=22, bottom=16,
                    alignment=ft.alignment.bottom_left,
                    content=ft.Image(src=p.logo_url, height=60,
                                     fit=ft.ImageFit.CONTAIN),
                )
            )
        hero = ft.Stack(hero_children, height=250)

        top_bar = ft.Container(
            padding=pad(14, 14, 14, 14),
            content=ft.Row(
                [
                    ft.Container(
                        width=38, height=38, bgcolor="#8c000000",
                        border_radius=30, alignment=ft.alignment.center,
                        on_click=lambda e: self.app.close_detail(),
                        content=ft.Icon(icons.ARROW_BACK, size=20, color="#fff"),
                    ),
                    ft.Container(width=10),
                    ft.Text(p.title, size=14, weight=ft.FontWeight.W_600,
                            color="#fff", max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                ],
                spacing=0,
            ),
        )
        return ft.Column(
            [
                top_bar,
                ft.ListView(
                    [
                        hero,
                        ft.Container(
                            padding=pad(22, 6, 22, 60),
                            content=ft.Column(body, spacing=0, tight=True),
                        ),
                    ],
                    expand=True, spacing=0,
                ),
            ],
            spacing=0, expand=True,
        )

    def _meta_line(self):
        p = self.post
        chips = []
        if p.rating is not None:
            chips.append(ft.Row(
                [ft.Icon(icons.STAR, size=13, color=ACCENT),
                 ft.Container(width=5),
                 ft.Text(f"{p.rating:.1f}", size=12, color=MUTED)],
                tight=True, spacing=0,
            ))
        if p.year:
            chips.append(ft.Row(
                [ft.Icon(icons.CALENDAR_TODAY, size=13, color=MUTED),
                 ft.Container(width=5),
                 ft.Text(str(p.year), size=12, color=MUTED)],
                tight=True, spacing=0,
            ))
        if p.duration:
            chips.append(ft.Row(
                [ft.Icon(icons.ACCESS_TIME, size=13, color=MUTED),
                 ft.Container(width=5),
                 ft.Text(p.duration, size=12, color=MUTED)],
                tight=True, spacing=0,
            ))
        elif p.kind == "show" and p.seasons:
            chips.append(ft.Row(
                [ft.Icon(icons.LAYERS_OUTLINED, size=13, color=MUTED),
                 ft.Container(width=5),
                 ft.Text(f"{len(p.seasons)} temporada{'s' if len(p.seasons) != 1 else ''}",
                         size=12, color=MUTED)],
                tight=True, spacing=0,
            ))
        return ft.Row(chips, wrap=True, spacing=14, run_spacing=8)

    def _actions(self):
        p = self.post
        saved = p.id in State.saved

        def on_save(e):
            if saved:
                State.saved.discard(p.id)
            else:
                State.saved.add(p.id)
            self.app.rebuild()

        def on_share(e):
            try:
                self.app.page.set_clipboard(p.link)
            except Exception:
                pass

        return ft.Row(
            [
                ft.Container(
                    expand=True, padding=padv(0, 12),
                    bgcolor=CARD if saved else ACCENT,
                    border=bord_all(1, ACCENT),
                    border_radius=RADIUS_SM,
                    alignment=ft.alignment.center,
                    on_click=on_save,
                    content=ft.Row(
                        [
                            ft.Icon(
                                icons.BOOKMARK_ADDED if saved else icons.BOOKMARK_OUTLINE,
                                size=16, color=ACCENT if saved else "#000",
                            ),
                            ft.Container(width=7),
                            ft.Text("Guardado" if saved else "Guardar",
                                    size=14, weight=ft.FontWeight.W_700,
                                    color=ACCENT if saved else "#000"),
                        ],
                        tight=True, spacing=0,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ),
                ft.Container(width=10),
                ft.Container(
                    expand=True, padding=padv(0, 12),
                    bgcolor=CARD, border=bord_all(1, CARD_BORDER),
                    border_radius=RADIUS_SM,
                    alignment=ft.alignment.center,
                    on_click=on_share,
                    content=ft.Row(
                        [
                            ft.Icon(icons.SHARE_OUTLINED, size=16, color=TEXT),
                            ft.Container(width=7),
                            ft.Text("Compartir", size=14,
                                    weight=ft.FontWeight.W_700, color=TEXT),
                        ],
                        tight=True, spacing=0,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ),
            ],
            spacing=0,
        )

    def _structured_body(self):
        p = self.post
        out = []
        if p.synopsis:
            out.append(ft.Text(p.synopsis, size=14, color="#cfced0"))
            out.append(ft.Container(height=8))
        if p.kind == "movie":
            out.append(self._server_picker(
                p.servers_by_language, p.default_lang,
                on_lang=self._set_lang,
                on_play=lambda: self._play_first(p.servers_by_language,
                                                 p.default_lang, p.title),
            ))
        elif p.kind == "show" and p.seasons:
            if len(p.seasons) > 1:
                out.append(ft.Row(
                    [ft.Container(
                        padding=padv(14, 7),
                        bgcolor=ACCENT_SOFT if self.season_index == i else CARD,
                        border=bord_all(1, ACCENT if self.season_index == i else CARD_BORDER),
                        border_radius=30,
                        on_click=lambda e, idx=i: self._set_season(idx),
                        content=ft.Text(f"Temporada {s.number}", size=13,
                                        color=ACCENT if self.season_index == i else MUTED,
                                        weight=ft.FontWeight.W_600 if self.season_index == i else ft.FontWeight.W_400),
                    ) for i, s in enumerate(p.seasons)],
                    scroll=ft.ScrollMode.ADAPTIVE, spacing=8,
                ))
                out.append(ft.Container(height=16))
            season = p.seasons[self.season_index]
            for ep in season.episodes:
                key = f"{season.number}-{ep.number}"
                out.append(self._episode_tile(ep, key))
        return out

    def _set_lang(self, lang):
        self.selected_lang = lang
        self.app.rebuild()

    def _set_season(self, idx):
        self.season_index = idx
        self.expanded_episode = None
        self.app.rebuild()

    def _toggle_episode(self, key):
        self.expanded_episode = None if self.expanded_episode == key else key
        self.app.rebuild()

    def _episode_tile(self, ep, key):
        p = self.post
        expanded = self.expanded_episode == key
        header = ft.Container(
            padding=pad(11, 11, 11, 11),
            on_click=lambda e: self._toggle_episode(key),
            content=ft.Row(
                [
                    poster(ep.still_url or p.img, width=96, height=64, radius=8),
                    ft.Container(width=11),
                    ft.Column(
                        [
                            ft.Text(f"{ep.number}. {ep.title}", size=13.5,
                                    weight=ft.FontWeight.W_700, color=TEXT,
                                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            *([ft.Container(
                                content=ft.Text(ep.synopsis, size=11.5,
                                                color=MUTED, max_lines=2,
                                                overflow=ft.TextOverflow.ELLIPSIS),
                            )] if ep.synopsis else []),
                            *([ft.Text(ep.duration, size=11, color=MUTED_SOFT)] if ep.duration else []),
                        ],
                        spacing=3, tight=True, expand=True,
                    ),
                    ft.Icon(
                        icons.KEYBOARD_ARROW_UP if expanded else icons.KEYBOARD_ARROW_DOWN,
                        size=16, color=MUTED_SOFT,
                    ),
                ],
                spacing=0,
            ),
        )
        children = [header]
        if expanded:
            children.append(
                ft.Container(
                    padding=pad(13, 0, 13, 15),
                    border=bord(t=side(1, CARD_BORDER)),
                    content=self._server_picker(
                        ep.servers, p.default_lang,
                        chosen=self.episode_langs.get(key),
                        on_lang=lambda lang, k=key: self._set_ep_lang(k, lang),
                        on_play=lambda ep_=ep: self._play_first(
                            ep_.servers, p.default_lang,
                            f"{p.title} · Episodio {ep_.number}"),
                    ),
                )
            )
        return ft.Container(
            margin=marg(0, 10, 0, 0),
            bgcolor=CARD, border=bord_all(1, CARD_BORDER),
            border_radius=RADIUS_MD,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Column(children, spacing=0, tight=True),
        )

    def _set_ep_lang(self, key, lang):
        self.episode_langs[key] = lang
        self.app.rebuild()

    def _server_picker(self, servers_map, default_lang, chosen=None,
                       on_lang=None, on_play=None):
        if not servers_map:
            return ft.Container(
                padding=pad(0, 14, 0, 0),
                content=ft.Text("Todavía no hay servidores cargados.",
                                color=MUTED_SOFT, size=13),
            )
        langs = list(servers_map.keys())
        active = chosen if (chosen in langs) else (
            default_lang if default_lang in langs else langs[0])
        servers = servers_map.get(active, [])
        lang_chips = [
            ft.Container(
                padding=padv(13, 7),
                bgcolor=ACCENT_SOFT if l == active else CARD,
                border=bord_all(1, ACCENT if l == active else CARD_BORDER),
                border_radius=30,
                on_click=(lambda e, lg=l: on_lang(lg)) if on_lang else None,
                content=ft.Text(l, size=12.5,
                                color=ACCENT if l == active else MUTED,
                                weight=ft.FontWeight.W_600 if l == active else ft.FontWeight.W_400),
            ) for l in langs
        ]
        server_chips = [
            ft.Container(
                padding=padv(13, 7),
                bgcolor=CARD, border=bord_all(1, CARD_BORDER), border_radius=30,
                content=ft.Text(s.name, size=12.5, color=MUTED),
            ) for s in servers
        ]
        return ft.Container(
            padding=pad(0, 14, 0, 0),
            content=ft.Column(
                [
                    ft.Row(
                        [ft.Icon(icons.LANGUAGE, size=14, color=ACCENT),
                         ft.Container(width=7),
                         ft.Text("Idioma", size=12.5,
                                 weight=ft.FontWeight.W_700, color=MUTED)],
                        tight=True, spacing=0,
                    ),
                    ft.Container(height=9),
                    ft.Row(lang_chips, wrap=True, spacing=8, run_spacing=8),
                    ft.Container(height=14),
                    ft.Row(
                        [ft.Icon(icons.DNS_OUTLINED, size=14, color=ACCENT),
                         ft.Container(width=7),
                         ft.Text("Servidor", size=12.5,
                                 weight=ft.FontWeight.W_700, color=MUTED)],
                        tight=True, spacing=0,
                    ),
                    ft.Container(height=9),
                    ft.Row(server_chips, wrap=True, spacing=8, run_spacing=8),
                    ft.Container(height=14),
                    ft.Container(
                        padding=padv(0, 14),
                        bgcolor=ACCENT if servers else MUTED_SOFT,
                        border_radius=RADIUS_SM,
                        alignment=ft.alignment.center,
                        on_click=on_play if servers else None,
                        content=ft.Row(
                            [ft.Icon(icons.PLAY_ARROW, size=18, color="#000"),
                             ft.Container(width=7),
                             ft.Text("Reproducir", size=14.5,
                                     weight=ft.FontWeight.W_700, color="#000")],
                            tight=True, spacing=0,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                    ),
                ],
                spacing=0, tight=True,
            ),
        )

    def _play_first(self, servers_map, default_lang, title):
        langs = list(servers_map.keys())
        if not langs:
            return
        active = self.selected_lang if self.selected_lang in langs else (
            default_lang if default_lang in langs else langs[0])
        servers = servers_map.get(active, [])
        if not servers:
            return
        self.app.open_player(servers[0], title)


# =========================================================================
#  VISTA: REPRODUCTOR
# =========================================================================
class PlayerView(ft.Container):
    def __init__(self, app, server, title):
        super().__init__(expand=True, bgcolor="#000")
        self.app = app
        self.server = server
        self.title = title
        self.status = ft.Text("Preparando reproducción…",
                              color="#e0e0e0", size=13, text_align=ft.TextAlign.CENTER)
        self.loader = ft.Container(
            alignment=ft.alignment.center, bgcolor="#d2000000",
            content=ft.Column(
                [ft.ProgressRing(color=ACCENT), ft.Container(height=16), self.status],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0,
            ),
            expand=True,
        )
        self.video_holder = ft.Container(expand=True, bgcolor="#000")
        self.content = ft.Column(
            [
                ft.Container(
                    padding=pad(16, 14, 16, 14), bgcolor="#000",
                    content=ft.Row(
                        [
                            ft.Container(
                                width=34, height=34, bgcolor="#1affffff",
                                border_radius=30, alignment=ft.alignment.center,
                                on_click=lambda e: self.app.close_player(),
                                content=ft.Icon(icons.ARROW_BACK, size=18, color="#fff"),
                            ),
                            ft.Container(width=12),
                            ft.Text(title, size=14, weight=ft.FontWeight.W_600,
                                    color="#fff", max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                        ],
                        spacing=0,
                    ),
                ),
                ft.Stack([self.video_holder, self.loader], expand=True),
            ],
            spacing=0, expand=True,
        )
        self.app.page.run_task(self._boot)

    def _set_status(self, text):
        self.status.value = text
        try: self.status.update()
        except Exception: pass

    def _hide_loader(self):
        self.loader.visible = False
        try: self.loader.update()
        except Exception: pass

    async def _boot(self):
        url = self.server.embed_url
        if not url:
            self._set_status("Este servidor no tiene URL.")
            return
        sig = f"{self.server.name} {self.server.internal_name or ''} {url}".lower()
        is_vidhide = "vidhide" in sig
        resolved = None
        if is_vidhide:
            self._set_status("Extrayendo enlace del servidor…")
            try:
                resolved = await asyncio.to_thread(resolve_vidhide, url)
            except Exception as e:
                print("Vidhide resolve falló:", e)
        if not resolved and re.search(r"\.(mp4|m3u8|webm|mkv|mov)(\?|$)", url, re.I):
            resolved = url
        if resolved and HAS_FTVIDEO:
            self._set_status("Cargando video…")
            try:
                # Flet nuevo: playlist es una lista de VideoMedia (sin Playlist).
                # Compat: si existe ftv.Playlist (API vieja), lo usamos.
                media = [ftv.VideoMedia(resolved)]
                if hasattr(ftv, "Playlist"):
                    playlist = ftv.Playlist(media)
                else:
                    playlist = media
                video = ftv.Video(
                    expand=True, autoplay=True,
                    playlist=playlist,
                )
                self.video_holder.content = video
                self.video_holder.update()
                await asyncio.sleep(1.2)
                self._hide_loader()
                return
            except Exception as e:
                print("Video init falló:", e)

        self._set_status("Cargando en modo seguro…")
        # WebView: en Flet nuevo vive en el paquete flet_webview;
        # en versiones viejas estaba en ft.WebView.
        wv_cls = None
        if HAS_FTWEBVIEW and hasattr(fwv, "WebView"):
            wv_cls = fwv.WebView
        elif hasattr(ft, "WebView"):
            wv_cls = ft.WebView
        if wv_cls is None:
            print("WebView no disponible (instala flet-webview).")
            self._hide_loader()
            self._set_status(
                "Reproductor web no disponible. Instala 'flet-webview' "
                "para reproducir este servidor."
            )
            return
        try:
            kwargs = dict(url=url, expand=True)
            # on_page_ended existía en la API vieja; la nueva usa on_page_ended
            # igualmente, pero lo envolvemos por si cambia el nombre.
            try:
                self.video_holder.content = wv_cls(
                    on_page_ended=lambda e: self._hide_loader(), **kwargs
                )
            except TypeError:
                self.video_holder.content = wv_cls(**kwargs)
                self._hide_loader()
            self.video_holder.update()
        except Exception as e:
            print("WebView falló:", e)
            self._hide_loader()
            self._set_status("No se pudo reproducir este título.")


# =========================================================================
#  APP
# =========================================================================
class App:
    def __init__(self, page):
        self.page = page
        self._setup_page()
        self.body = ft.Container(expand=True)
        self.current_tab = 0
        self.nav_row = self._build_nav()
        self.root = ft.Column(
            [
                ft.Container(expand=True, content=self.body),
                self.nav_row,
            ],
            spacing=0, expand=True,
        )
        page.add(self.root)
        self.switch_tab(0)
        page.run_task(self._load_feed)

    def _setup_page(self):
        p = self.page
        p.title = "Fotograma"
        p.bgcolor = BG
        p.padding = 0
        p.spacing = 0
        p.theme_mode = ft.ThemeMode.DARK
        try:
            p.window.width = 420
            p.window.height = 820
        except Exception:
            pass

    async def _load_feed(self):
        try:
            posts = await asyncio.to_thread(FeedService.load_all)
            State.posts = posts
            State.loading = False
            State.error = None
        except Exception as e:
            print("feed error:", e)
            State.loading = False
            State.error = str(e)
        self.switch_tab(self.current_tab)

    def _build_nav(self):
        tabs = [
            ("Inicio", icons.HOME_OUTLINED),
            ("Mis listas", icons.BOOKMARK_OUTLINE),
            ("Explorar", icons.EXPLORE_OUTLINED),
            ("Ajustes", icons.SETTINGS_OUTLINED),
        ]
        items = []
        for i, (label, icon) in enumerate(tabs):
            active = i == self.current_tab
            items.append(
                ft.Container(
                    expand=True, padding=pad(6, 6, 6, 6),
                    on_click=lambda e, idx=i: self.switch_tab(idx),
                    content=ft.Column(
                        [
                            ft.Icon(icon, size=22,
                                    color=ACCENT if active else MUTED_SOFT),
                            ft.Container(height=4),
                            ft.Text(label, size=11,
                                    color=ACCENT if active else MUTED_SOFT),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0, tight=True,
                    ),
                )
            )
        return ft.Container(
            bgcolor=BG_RAISED,
            border=bord(t=side(1, CARD_BORDER)),
            padding=padv(0, 9),
            content=ft.Row(items, spacing=0),
        )

    def _refresh_nav(self):
        new_nav = self._build_nav()
        self.root.controls[1] = new_nav
        self.nav_row = new_nav
        try: self.root.update()
        except Exception: pass

    def switch_tab(self, index):
        self.current_tab = index
        if index == 0:
            self.body.content = HomeView(self)
        elif index == 1:
            self.body.content = ListsView(self)
        elif index == 2:
            self.body.content = ExploreView(self)
        else:
            self.body.content = SettingsView(self)
        self._refresh_nav()
        try: self.body.update()
        except Exception: pass

    def rebuild(self):
        self.switch_tab(self.current_tab)
        if len(self.page.views) > 1:
            top = self.page.views[-1]
            if top.route == "/detail":
                controls = top.controls or []
                if controls and isinstance(controls[0], DetailView):
                    pid = controls[0].post.id if controls[0].post else None
                    if pid:
                        top.controls = [DetailView(self, pid)]
                        try: self.page.update()
                        except Exception: pass

    def open_detail(self, post_id):
        self.page.views.append(
            ft.View(route="/detail", controls=[DetailView(self, post_id)],
                    padding=0, bgcolor=BG, spacing=0)
        )
        self.page.update()

    def close_detail(self):
        if len(self.page.views) > 1:
            self.page.views.pop()
            self.page.update()

    def open_player(self, server, title):
        self.page.views.append(
            ft.View(route="/player", controls=[PlayerView(self, server, title)],
                    padding=0, bgcolor="#000", spacing=0)
        )
        self.page.update()

    def close_player(self):
        if len(self.page.views) > 1:
            self.page.views.pop()
            self.page.update()


def main(page):
    App(page)


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")