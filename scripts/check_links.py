#!/usr/bin/env python3
"""Checks every external http(s) link in the repository's Markdown, and every relative Markdown link.

    python3 scripts/check_links.py [--external]

Relative links are always checked (fast, offline). External links are requested once each with a
short timeout only with --external. A 401, 403, or 429 is reported as "blocked to automation", not
as broken, because several publishers refuse scripts (the source register records the same).
Prints one line per problem and a summary; exits 1 only for a broken relative link or an external
link that is missing (404, 410) or unreachable.
"""

import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\]\(([^)\s]+)\)|<(https?://[^>\s]+)>|(?<![\(\"'<])\b(https?://[^\s)>\]\"'`]+)")
SKIP_DIRS = {"node_modules", ".git", ".next", ".venv", "coverage", "test-results"}


def markdown_files():
    for path in ROOT.rglob("*.md"):
        if not (set(path.relative_to(ROOT).parts) & SKIP_DIRS):
            yield path


def main() -> int:
    external = "--external" in sys.argv
    broken: list[str] = []
    blocked: list[str] = []
    urls: dict[str, set[str]] = {}
    checked = 0
    for path in markdown_files():
        text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
        for match in LINK.finditer(text):
            target = next(group for group in match.groups() if group)
            target = target.rstrip(".,;:")
            if "<" in target or ">" in target:
                continue
            if target.startswith(("http://", "https://")):
                urls.setdefault(target, set()).add(str(path.relative_to(ROOT)))
            elif target.startswith(("mailto:", "#")) or "{" in target:
                continue
            else:
                checked += 1
                file_part = target.split("#", 1)[0]
                if file_part and not (path.parent / file_part).resolve().exists():
                    broken.append(f"BROKEN relative link {target} in {path.relative_to(ROOT)}")
    if external:
        context = ssl.create_default_context()
        for url, where in sorted(urls.items()):
            if "example" in url or "localhost" in url or "127.0.0.1" in url or ".test" in url or ".invalid" in url:
                continue
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (link check)"})
            try:
                with urllib.request.urlopen(request, timeout=15, context=context) as response:
                    checked += 1
                    if response.status >= 400:
                        broken.append(f"BROKEN {response.status} {url} in {sorted(where)[0]}")
            except urllib.error.HTTPError as error:
                checked += 1
                (blocked if error.code in (401, 403, 429) else broken).append(
                    f"{'BLOCKED' if error.code in (401, 403, 429) else 'BROKEN'} {error.code} {url} in {sorted(where)[0]}"
                )
            except Exception as error:  # noqa: BLE001 - any network failure is a finding
                broken.append(f"UNREACHABLE {url} ({type(error).__name__}) in {sorted(where)[0]}")
    for line in broken + blocked:
        print(line)
    print(f"checked {checked} links; {len(broken)} broken, {len(blocked)} blocked to automation")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
