"""Exercise media catalog, sourced from the Asterisk project.

Asterisk holds 3,557 exercises with an image, a thumbnail and a demo video
each, plus a master CSV of descriptions, muscles, equipment and execution
tips. This module maps our exercise keys onto that library.

We never copy the media -- 933 MB stays where it is and we reference it by
absolute path. What we do build is a slim local index so that starting a
session does not mean parsing a 10 MB CSV.

    python -m trainer.catalog --build
    python -m trainer.catalog --search "bulgarian split"
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

ASTERISK_ROOT = Path("E:/AsteriskBetav3/production/backend")
SOURCE_CSV = ASTERISK_ROOT / "data" / "esercizi_import_completo.csv"
MEDIA_ROOT = ASTERISK_ROOT / "static" / "exercises"

INDEX_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.json"

# Suffixes Asterisk strips when naming media files.
_NOISE = re.compile(r"\s*\((?:female|male|m|f)\)\s*", re.IGNORECASE)


def slugify(name: str) -> str:
    """Match Asterisk's slug rule: fold accents, lowercase, hyphenate."""
    name = _NOISE.sub(" ", name)
    ascii_only = (unicodedata.normalize("NFKD", name)
                  .encode("ascii", "ignore").decode("ascii"))
    return re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-") or "exercise"


@dataclass
class CatalogEntry:
    slug: str
    name: str
    category: str = ""
    kind: str = ""              # tipologia, e.g. Forza / Mobilita
    description: str = ""       # Italian
    muscles_primary: str = ""
    muscles_secondary: str = ""
    equipment: str = ""
    tips: str = ""              # suggerimenti_esecuzione, Italian
    image: str = ""
    thumb: str = ""
    video: str = ""

    @property
    def has_media(self) -> bool:
        return bool(self.image or self.video)


def _media_for(slug: str, available: dict[str, set[str]]) -> tuple[str, str, str]:
    def find(kind: str, ext: str) -> str:
        if slug in available[kind]:
            return str(MEDIA_ROOT / kind / f"{slug}.{ext}")
        return ""
    return find("img", "webp"), find("thumb", "webp"), find("video", "mp4")


def build_index(verbose: bool = True) -> list[CatalogEntry]:
    """Parse the Asterisk CSV and resolve each row to its media files."""
    if not SOURCE_CSV.exists():
        raise FileNotFoundError(
            f"Asterisk catalog not found at {SOURCE_CSV}.\n"
            f"Edit ASTERISK_ROOT in trainer/catalog.py if the project moved."
        )

    available = {
        kind: {p.stem for p in (MEDIA_ROOT / kind).glob(f"*.{ext}")}
        for kind, ext in (("img", "webp"), ("thumb", "webp"), ("video", "mp4"))
    }
    if verbose:
        print(f"media on disk: " + ", ".join(
            f"{k} {len(v)}" for k, v in available.items()))

    csv.field_size_limit(10 ** 9)
    entries: list[CatalogEntry] = []
    seen: set[str] = set()

    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("nome_esercizio") or "").strip()
            if not name:
                continue
            slug = slugify(name)
            if slug in seen:
                continue
            seen.add(slug)
            image, thumb, video = _media_for(slug, available)
            entries.append(CatalogEntry(
                slug=slug,
                name=_NOISE.sub("", name).strip(),
                category=(row.get("categoria") or "").strip(),
                kind=(row.get("tipologia") or "").strip(),
                description=(row.get("descrizione") or "").strip(),
                muscles_primary=(row.get("muscoli_principali") or "").strip(),
                muscles_secondary=(row.get("muscoli_secondari") or "").strip(),
                equipment=(row.get("strumenti_necessari") or "").strip(),
                tips=(row.get("suggerimenti_esecuzione") or "").strip(),
                image=image, thumb=thumb, video=video,
            ))

    if verbose:
        with_media = sum(1 for e in entries if e.has_media)
        with_video = sum(1 for e in entries if e.video)
        print(f"parsed {len(entries)} unique exercises")
        print(f"  resolved media: {with_media} ({with_media / len(entries):.0%})")
        print(f"  with video:     {with_video} ({with_video / len(entries):.0%})")
    return entries


def save_index(entries: list[CatalogEntry]) -> Path:
    INDEX_PATH.parent.mkdir(exist_ok=True)
    INDEX_PATH.write_text(
        json.dumps([asdict(e) for e in entries], ensure_ascii=False),
        encoding="utf-8",
    )
    return INDEX_PATH


_CACHE: dict[str, CatalogEntry] | None = None


def load_index() -> dict[str, CatalogEntry]:
    """Slug -> entry, built on first use and cached in memory."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if not INDEX_PATH.exists():
        save_index(build_index(verbose=False))
    raw = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    _CACHE = {d["slug"]: CatalogEntry(**d) for d in raw}
    return _CACHE


def search(query: str, limit: int = 12, media_only: bool = True) -> list[CatalogEntry]:
    """Rank catalog entries against a query by token overlap.

    Deliberately simple: the catalog is small enough that a scan is instant,
    and exact-token matching beats fuzzy matching for names this formulaic.
    """
    index = load_index()
    terms = [t for t in re.split(r"[^a-z0-9]+", query.lower()) if t]
    if not terms:
        return []

    scored: list[tuple[float, CatalogEntry]] = []
    for entry in index.values():
        if media_only and not entry.has_media:
            continue
        slug_terms = entry.slug.split("-")
        hits = sum(1 for t in terms if t in slug_terms)
        if not hits:
            # Substring fallback catches "bulgarian" inside a longer token.
            hits = sum(0.5 for t in terms if t in entry.slug)
            if not hits:
                continue
        # Prefer names that are mostly the query rather than the query plus
        # five other words, and prefer entries that have a demo video.
        score = hits / len(terms) - 0.03 * len(slug_terms) + (0.3 if entry.video else 0)
        scored.append((score, entry))

    scored.sort(key=lambda s: -s[0])
    return [e for _, e in scored[:limit]]


def resolve(slug_or_query: str) -> CatalogEntry | None:
    index = load_index()
    if slug_or_query in index:
        return index[slug_or_query]
    hits = search(slug_or_query, limit=1)
    return hits[0] if hits else None


def main() -> int:
    p = argparse.ArgumentParser(description="Asterisk exercise catalog")
    p.add_argument("--build", action="store_true", help="rebuild the local index")
    p.add_argument("--search", metavar="QUERY")
    args = p.parse_args()

    if args.build:
        entries = build_index()
        path = save_index(entries)
        print(f"wrote {path} ({path.stat().st_size / 1e6:.1f} MB)")
        return 0

    if args.search:
        hits = search(args.search)
        if not hits:
            print("no matches")
            return 1
        for e in hits:
            media = "V" if e.video else ("I" if e.image else "-")
            print(f"  [{media}] {e.slug:52s} {e.category}")
        return 0

    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
