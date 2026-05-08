#!/usr/bin/env python3
"""Bulk seed flashcards via the local API.
To do: 
    Criar um arquivo de snapshot das questões do banco e versionar no git.
Usage:
    python3 seed.py cards.json [--api http://localhost:8000]

Input file format: JSON list of card objects matching CardCreate
(topics, question, options, correct_answer, [explanation], [difficulty]).
"""
import argparse
import json
import sys
import urllib.error
import urllib.request


def post_card(api_url: str, card: dict) -> dict:
    req = urllib.request.Request(
        f"{api_url}/api/cards",
        data=json.dumps(card).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def main() -> int:
    p = argparse.ArgumentParser(description="Bulk seed flashcards via API")
    p.add_argument("file", help="JSON file with a list of cards")
    p.add_argument("--api", default="http://localhost:8000", help="API base URL")
    args = p.parse_args()

    with open(args.file, encoding="utf-8") as f:
        cards = json.load(f)

    if not isinstance(cards, list):
        print("error: file must contain a JSON list of cards", file=sys.stderr)
        return 1

    ok = 0
    failures: list[tuple[int, str]] = []
    total = len(cards)

    for i, card in enumerate(cards, 1):
        try:
            res = post_card(args.api, card)
            preview = (res.get("question") or "")[:60]
            print(f"[{i}/{total}] ok id={res['id']} {preview}")
            ok += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:300]
            failures.append((i, f"HTTP {e.code}: {body}"))
            print(f"[{i}/{total}] FAIL HTTP {e.code}", file=sys.stderr)
        except urllib.error.URLError as e:
            failures.append((i, f"connection: {e.reason}"))
            print(f"[{i}/{total}] FAIL connection: {e.reason}", file=sys.stderr)

    print(f"\n{ok}/{total} cards seeded")
    if failures:
        print("failures:", file=sys.stderr)
        for idx, msg in failures:
            print(f"  #{idx}: {msg}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
