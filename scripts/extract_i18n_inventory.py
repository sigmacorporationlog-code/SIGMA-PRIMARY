"""Inventorie les chaînes UI candidates à l’internationalisation.

Le script est non destructif: il produit un inventaire JSON pour terminer la
migration FR/EN sans perdre une chaîne existante.
"""
from pathlib import Path
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1]
TEXT_RE = re.compile(r">([^<>]{3,120})<")
ATTR_RE = re.compile(r"""(?:placeholder|title|alt|aria-label)\s*=\s*["']([^"']{3,120})["']""", re.I)

def main():
    values = set()
    for path in list((ROOT / "static").rglob("*.html")) + list((ROOT / "mobile").rglob("*.html")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in (TEXT_RE, ATTR_RE):
            for match in pattern.findall(text):
                value = html.unescape(" ".join(match.split()))
                if value and not value.startswith("{{") and not value.startswith("{%"):
                    values.add(value)
    output = ROOT / "i18n" / "inventory.json"
    output.write_text(json.dumps(sorted(values), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(values)} chaînes candidates -> {output}")

if __name__ == "__main__":
    main()
