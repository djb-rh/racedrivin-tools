#!/usr/bin/env python3
"""Turn a small Markdown subset into BBCode and HTML for pasting into web forums.

    python3 tools/forumpost.py STATUS.md          # writes STATUS.bbcode and STATUS.html
    python3 tools/forumpost.py STATUS.md --check  # exit 1 if those are out of date

Supported Markdown: #/##/### headings, paragraphs, "- " bullets (two-space
indent for one nested level), **bold**, *italic*, `code`, [text](url) and bare
http(s) URLs.  Nothing else, on purpose: forum markup is lowest common
denominator (no tables, no sizes), so the source stays in that subset too.
"""
import html
import re
import sys
from pathlib import Path

INLINE = re.compile(
    r"\[([^\]]+)\]\((https?://[^)\s]+)\)"   # 1,2 markdown link
    r"|(\*\*)(.+?)\*\*"                     # 3,4 bold
    r"|(?<!\*)\*([^*\n]+?)\*(?!\*)"         # 5 italic
    r"|`([^`]+)`"                           # 6 code
    r"|(https?://[^\s<>()\[\]]+?)(?=[.,;:)]*(?:\s|$))"  # 7 bare URL
)


def inline(text, fmt):
    esc = html.escape if fmt == "html" else (lambda s: s)

    def repl(m):
        if m.group(1):
            t, u = esc(m.group(1)), m.group(2)
            return f'<a href="{u}">{t}</a>' if fmt == "html" else f"[url={u}]{t}[/url]"
        if m.group(3):
            t = inline(m.group(4), fmt)
            return f"<b>{t}</b>" if fmt == "html" else f"[b]{t}[/b]"
        if m.group(5):
            t = inline(m.group(5), fmt)
            return f"<i>{t}</i>" if fmt == "html" else f"[i]{t}[/i]"
        if m.group(6):
            t = esc(m.group(6))
            return f"<code>{t}</code>" if fmt == "html" else t
        u = m.group(7)
        return f'<a href="{u}">{u}</a>' if fmt == "html" else f"[url]{u}[/url]"

    out, pos = [], 0
    for m in INLINE.finditer(text):
        out.append(esc(text[pos:m.start()]))
        out.append(repl(m))
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


def blocks(src):
    """Yield ('h', level, text), ('p', text) or ('list', [(depth, text), ...])."""
    lines = src.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = re.match(r"(#{1,3})\s+(.*)", line)
        if m:
            yield ("h", len(m.group(1)), m.group(2).strip())
            i += 1
            continue
        if re.match(r"\s*-\s+", line):
            items = []
            while i < len(lines) and lines[i].strip():
                m = re.match(r"(\s*)-\s+(.*)", lines[i])
                if m:
                    items.append([len(m.group(1)) // 2, m.group(2).strip()])
                else:  # continuation line of the previous item
                    items[-1][1] += " " + lines[i].strip()
                i += 1
            yield ("list", [tuple(x) for x in items])
            continue
        para = []
        while i < len(lines) and lines[i].strip() and not re.match(r"(#{1,3}\s|\s*-\s)", lines[i]):
            para.append(lines[i].strip())
            i += 1
        yield ("p", " ".join(para))


def render_list(items, fmt):
    out = []
    depth = -1
    for d, text in items:
        while depth < d:
            out.append("<ul>" if fmt == "html" else "[list]")
            depth += 1
        while depth > d:
            out.append("</ul>" if fmt == "html" else "[/list]")
            depth -= 1
        t = inline(text, fmt)
        out.append(f"<li>{t}</li>" if fmt == "html" else f"[*]{t}")
    while depth >= 0:
        out.append("</ul>" if fmt == "html" else "[/list]")
        depth -= 1
    return "\n".join(out)


def render(src, fmt):
    out = []
    for b in blocks(src):
        if b[0] == "h":
            level, text = b[1], inline(b[2], fmt)
            if fmt == "html":
                out.append(f"<h{level}>{text}</h{level}>")
            elif level <= 2:
                out.append(f"[b][u]{text}[/u][/b]")
            else:
                out.append(f"[b]{text}[/b]")
        elif b[0] == "p":
            text = inline(b[1], fmt)
            out.append(f"<p>{text}</p>" if fmt == "html" else text)
        else:
            out.append(render_list(b[1], fmt))
    body = "\n\n".join(out) + "\n"
    if fmt == "html":
        return body
    return body


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    if len(args) != 1:
        sys.exit(__doc__)
    src = Path(args[0])
    text = src.read_text()
    stale = []
    for fmt, suffix in (("bbcode", ".bbcode"), ("html", ".html")):
        out = src.with_suffix(suffix)
        rendered = render(text, fmt)
        if check:
            if not out.exists() or out.read_text() != rendered:
                stale.append(out.name)
        else:
            out.write_text(rendered)
            print(f"wrote {out}")
    if stale:
        sys.exit("out of date: " + ", ".join(stale) + f"  (run: python3 {sys.argv[0]} {src})")


if __name__ == "__main__":
    main()
