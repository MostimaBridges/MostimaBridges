#!/usr/bin/env python3
"""Validate README.md, its local assets, and the workflow files.

Run locally or from CI (`.github/workflows/readme-check.yml`). Exits non-zero on
any error; warnings do not fail the build.

Checks
------
README.md
  * every relative ``src`` / ``srcset`` / ``href`` target exists on disk
  * no absolute local paths (``C:\\``, ``D:\\``, ``E:\\``, ``file://``)
  * no bare comma in a ``srcset`` (HTML would read it as a candidate separator
    and silently truncate the URL)
  * every ``<img>`` has an ``alt`` attribute, and it is not a placeholder
  * every ``<picture>`` has at least one ``<source>`` and a fallback ``<img>``
  * ``<picture>`` / ``<div>`` / ``<p>`` / ``<table>`` tags are balanced
  * no ``style=`` attributes (GitHub strips them; relying on them is a bug)
  * no secret-looking strings, private-repo URLs, or leftover TODO markers

assets/
  * referenced local assets are non-empty and within a per-file size budget
  * reports total committed asset weight

.github/workflows/*.yml
  * ``workflow_dispatch`` is present
  * every third-party ``uses:`` is pinned to a full 40-character commit SHA
    and annotated with the release tag it corresponds to
  * a top-level ``permissions:`` block exists, and jobs that push declare
    ``contents: write``
  * ``concurrency:`` is present
  * scheduled crons avoid minute 0 (GitHub queues those runs)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"
WORKFLOWS = REPO / ".github" / "workflows"

# Files produced by CI, so they are legitimately absent from a fresh checkout.
GENERATED_BY_CI = {
    "assets/generated/snake-dark.svg",
    "assets/generated/snake-light.svg",
}

PER_FILE_BUDGET_KB = 500
REPO_BUDGET_KB = 4096

PLACEHOLDER_ALTS = {"", "image", "img", "picture", "screenshot", "banner", "logo", "icon", "graphic"}
SECRET_PATTERNS = [
    (r"\bsk-[A-Za-z0-9]{16,}", "looks like an API key"),
    (r"\bgh[pousr]_[A-Za-z0-9]{16,}", "looks like a GitHub token"),
    (r"\bAKIA[0-9A-Z]{16}\b", "looks like an AWS access key id"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "embedded private key"),
    (r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*[\"']?[^\s\"'<>]{6,}",
     "hard-coded credential"),
]
# Private infrastructure that must never appear on a public profile.
LEAK_PATTERNS = [
    (r"\b(?:10|127)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "private or loopback IP"), 
    (r"\b192\.168\.\d{1,3}\.\d{1,3}\b", "private IP"),
    (r"\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b", "private IP"),
    (r"https?://[^\s\"'<>)]*\.(?:local|internal|lan)\b", "internal hostname"),
    (r"(?i)\b(?:ssh|sftp)://", "ssh url"),
    (r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb|redis)://[^\s\"'<>)]*:[^\s\"'<>@]*@", "database URL with credentials"),
]

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


# ─────────────────────────────────────────────────────────────────────────────
# README
# ─────────────────────────────────────────────────────────────────────────────


def is_external(url: str) -> bool:
    return url.startswith(("http://", "https://", "mailto:", "#", "data:"))


# HTML comments are stripped before structural checks: a maintainer note may
# legitimately quote markup (``<img>``, ``<div align="center">``) as prose.
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

# GitHub's image proxy caches by URL, so a ``?v=2`` query is the documented way
# to bust it. Query strings and fragments are not part of the on-disk path.
URL_SUFFIX = re.compile(r"[?#].*$")


def check_readme() -> None:
    if not README.exists():
        err("README.md is missing")
        return

    raw = README.read_text(encoding="utf-8")
    text = HTML_COMMENT.sub("", raw)

    # ── HTML hygiene ───────────────────────────────────────────────────────
    for tag in ("picture", "div", "p", "table", "sub", "details"):
        opened = len(re.findall(rf"<{tag}(?=[\s>])", text))
        closed = len(re.findall(rf"</{tag}>", text))
        if opened != closed:
            err(f"<{tag}> unbalanced in README.md: {opened} opened, {closed} closed")

    if re.search(r"\sstyle\s*=", text):
        err("README.md uses a style= attribute; GitHub strips these")

    # HTML splits srcset on every comma, whitespace or not, so a comma inside a
    # URL silently truncates the value to its first candidate. skillicons.dev
    # takes its icon list as `?i=py,ts,js`, which GitHub therefore rewrites to
    # `?i=py`: the row keeps one icon and drops the other seven. Encode it.
    for m in re.finditer(r"\bsrcset\s*=\s*\"([^\"]*)\"", text):
        value = m.group(1)
        if "," in value:
            err(
                "srcset holds a bare comma in "
                f"{value[:60]!r}; HTML reads it as a candidate separator and keeps "
                "only what precedes it. Percent-encode it as %2C."
            )

    # ── images: alt text ──────────────────────────────────────────────────
    for m in re.finditer(r"<img\b[^>]*>", text, re.DOTALL):
        tag = m.group(0)
        alt = re.search(r"\balt\s*=\s*\"([^\"]*)\"", tag, re.DOTALL)
        if alt is None:
            err(f"<img> without alt: {tag[:90]}...")
        elif alt.group(1).strip().lower() in PLACEHOLDER_ALTS and not is_decorative(tag):
            err(f"<img> has a placeholder alt ({alt.group(1)!r}); describe the content or use alt=\"\" if decorative")
        src = re.search(r"\bsrc\s*=\s*\"([^\"]+)\"", tag)
        if src is None:
            err(f"<img> without src: {tag[:90]}...")

    # ── picture: source + fallback ────────────────────────────────────────
    for m in re.finditer(r"<picture>(.*?)</picture>", text, re.DOTALL):
        body = m.group(1)
        if "<source" not in body:
            err("<picture> block has no <source>; a plain <img> would do")
        if "<img" not in body:
            err("<picture> block has no fallback <img>")
        if "prefers-color-scheme" not in body:
            warn("<picture> block does not use prefers-color-scheme")

    # ── local references resolve ──────────────────────────────────────────
    refs: set[str] = set()
    for attr in ("src", "srcset", "href"):
        for m in re.finditer(rf"\b{attr}\s*=\s*\"([^\"]+)\"", text):
            value = m.group(1)
            # HTML splits srcset candidates on every comma, whitespace or not.
            # A bare comma is already an error above, so a srcset that reaches
            # this point holds a single candidate; the `2x` / `640w` descriptor,
            # if one is present, is dropped together with its leading space.
            candidate = value.strip().split(" ")[0].strip()
            candidate = URL_SUFFIX.sub("", candidate)
            if candidate and not is_external(candidate):
                refs.add(candidate)

    for ref in sorted(refs):
        target = ref[2:] if ref.startswith("./") else ref
        if target in GENERATED_BY_CI:
            if not (REPO / target).exists():
                warn(f"{target} is CI-generated and not present yet (run the snake workflow once)")
            continue
        path = REPO / target
        if not path.exists():
            err(f"README.md references a missing file: {ref}")
        elif path.is_file() and path.stat().st_size == 0:
            err(f"README.md references an empty file: {ref}")

    # ── no local machine paths ────────────────────────────────────────────
    # These scans deliberately run against `raw`, comments included: a secret or
    # a machine path inside an HTML comment is still committed and still public.
    for m in re.finditer(r"\b[A-Za-z]:\\[^\s\"'<>)]*", raw):
        err(f"absolute local path in README.md: {m.group(0)}")
    if "file://" in raw:
        err("README.md contains a file:// URL")

    # ── no secrets, no private infrastructure ─────────────────────────────
    for pattern, label in SECRET_PATTERNS + LEAK_PATTERNS:
        for m in re.finditer(pattern, raw):
            err(f"README.md contains a {label}: {m.group(0)[:60]}")
    for m in re.finditer(r"github\.com/[A-Za-z0-9_.-]+/([A-Za-z0-9_.-]+)", raw):
        if m.group(1) not in ("MostimaBridges",):
            warn(f"README.md links to another repository ({m.group(0)}); confirm it is public")

    if "TODO(USER)" in raw or "TODO:" in raw:
        err("README.md still contains a TODO marker")

    check_tone(text)


# Marketing register and LLM-summary sentence shapes. These are warnings, not
# errors: any single one can be legitimate, but a page that accumulates them
# reads like generated copy instead of a person's own page.
TONE_PATTERNS = [
    (r"端到端", "宣传词「端到端」"),
    (r"生产级", "宣传词「生产级」"),
    (r"企业级", "宣传词「企业级」"),
    (r"强大的", "宣传词「强大的」"),
    (r"先进的", "宣传词「先进的」"),
    (r"全面的", "宣传词「全面的」"),
    (r"高性能", "宣传词「高性能」"),
    (r"高度可靠", "宣传词「高度可靠」"),
    (r"鲁棒", "宣传词「鲁棒」"),
    (r"无缝", "宣传词「无缝」"),
    (r"赋能", "宣传词「赋能」"),
    (r"核心能力", "总结腔「核心能力」"),
    (r"技术亮点", "总结腔「技术亮点」"),
    (r"工程实践", "总结腔「工程实践」"),
    (r"架构层面", "总结腔「架构层面」"),
    (r"值得注意", "总结腔「值得注意」"),
    (r"与此同时", "总结腔「与此同时」"),
    (r"综上所述", "总结腔「综上所述」"),
    (r"该系统", "总结腔「该系统」"),
    (r"该项目采用", "总结腔「该项目采用」"),
    (r"不是[^。；\n]{1,24}而是", "AI 高频句式「不是……而是……」"),
    (r"不仅[^。；\n]{1,24}而且", "AI 高频句式「不仅……而且……」"),
    (r"(?i)\bend-to-end\b", 'marketing word "end-to-end"'),
    (r"(?i)\bproduction-grade\b", 'marketing word "production-grade"'),
    (r"(?i)\brobust\b", 'marketing word "robust"'),
    (r"(?i)\bseamless\b", 'marketing word "seamless"'),
    (r"(?i)\bcomprehensive\b", 'marketing word "comprehensive"'),
    (r"(?i)\bcutting-edge\b", 'marketing word "cutting-edge"'),
    (r"(?i)\bpowerful\b", 'marketing word "powerful"'),
]


def check_tone(text: str) -> None:
    for pattern, label in TONE_PATTERNS:
        for m in re.finditer(pattern, text):
            warn(f"tone: {label} -> {m.group(0)!r}")


def is_decorative(tag: str) -> bool:
    """Decorative images may legitimately use an empty alt."""
    return bool(re.search(r"\balt\s*=\s*\"\"", tag))


# ─────────────────────────────────────────────────────────────────────────────
# ASSETS
# ─────────────────────────────────────────────────────────────────────────────


def check_assets() -> None:
    assets = REPO / "assets"
    if not assets.is_dir():
        err("assets/ directory is missing")
        return

    total = 0
    for path in sorted(assets.rglob("*")):
        if not path.is_file() or path.name == "README.md":
            continue
        rel = path.relative_to(REPO).as_posix()
        size = path.stat().st_size
        total += size
        if size == 0:
            err(f"empty asset: {rel}")
        elif size / 1024 > PER_FILE_BUDGET_KB:
            err(f"asset exceeds {PER_FILE_BUDGET_KB} KB: {rel} ({size / 1024:.0f} KB)")

    if total / 1024 > REPO_BUDGET_KB:
        err(f"committed assets total {total / 1024:.0f} KB, over the {REPO_BUDGET_KB} KB budget")
    else:
        print(f"assets: {total / 1024:.0f} KB total (budget {REPO_BUDGET_KB} KB)")


# ─────────────────────────────────────────────────────────────────────────────
# WORKFLOWS
# ─────────────────────────────────────────────────────────────────────────────


def check_workflows() -> None:
    if not WORKFLOWS.is_dir():
        warn("no .github/workflows directory")
        return

    files = sorted(list(WORKFLOWS.glob("*.yml")) + list(WORKFLOWS.glob("*.yaml")))
    if not files:
        warn("no workflow files found")
        return

    for wf in files:
        rel = wf.relative_to(REPO).as_posix()
        text = wf.read_text(encoding="utf-8")

        if "workflow_dispatch:" not in text:
            err(f"{rel}: missing workflow_dispatch (manual runs must stay possible)")
        if not re.search(r"^permissions:", text, re.MULTILINE):
            err(f"{rel}: missing a top-level permissions block")
        if not re.search(r"^concurrency:", text, re.MULTILINE):
            err(f"{rel}: missing concurrency")

        pushes = bool(re.search(r"^\s+contents:\s*write", text, re.MULTILINE))
        if pushes and not re.search(r"^\s+contents:\s*read", text, re.MULTILINE):
            warn(f"{rel}: grants contents: write without an explicit read default")

        for m in re.finditer(r"^\s*-?\s*uses:\s*(\S+)", text, re.MULTILINE):
            spec = m.group(1).strip().strip("\"'")
            if spec.startswith("./"):
                continue
            if "@" not in spec:
                err(f"{rel}: uses: {spec} has no ref")
                continue
            ref = spec.rsplit("@", 1)[1]
            if not re.fullmatch(r"[0-9a-f]{40}", ref):
                err(f"{rel}: uses: {spec} is not pinned to a full commit SHA")
            line = text[m.start(): text.find("\n", m.start())]
            if "#" not in line:
                warn(f"{rel}: pinned action {spec.split('@')[0]} has no '# vX.Y.Z' comment")

        for m in re.finditer(r"cron:\s*[\"']([^\"']+)[\"']", text):
            fields = m.group(1).split()
            if len(fields) >= 2 and fields[0] == "0" and fields[1].isdigit():
                err(f"{rel}: cron '{m.group(1)}' runs on the hour; pick an off-peak minute")

        if "GITHUB_TOKEN" in text or "secrets." in text:
            for m in re.finditer(r"secrets\.([A-Za-z0-9_]+)", text):
                if m.group(1) != "GITHUB_TOKEN":
                    warn(f"{rel}: uses secret {m.group(1)}; confirm it is required")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    print(f"checking {REPO}")
    check_readme()
    check_assets()
    check_workflows()

    for w in warnings:
        print(f"  WARN  {w}")
    for e in errors:
        print(f"  FAIL  {e}")

    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
