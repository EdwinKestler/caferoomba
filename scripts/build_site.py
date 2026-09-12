#!/usr/bin/env python3
"""Build an allowlisted static site without importing or executing robot code.

Only documents in site/documents.json and explicitly approved public assets are
included. Private media, credentials, runtime artifacts and Project Memory never
enter the published tree. Markdown raw HTML is disabled. Output is disposable.
"""
from __future__ import annotations
import argparse
import html
import json
import os
import re
import shutil
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit, urlunsplit
from markdown_it import MarkdownIt

REPO = 'https://github.com/EdwinKestler/caferoomba'
PUBLIC_URL = 'https://edwinkestler.github.io/caferoomba/'
ASSETS = ('style.css', 'site.js', 'favicon.svg', 'robot-patio.webp', 'patio.webp', 'prototype.webp')


def slug(text: str) -> str:
    return re.sub(r'[^a-z0-9-]', '', re.sub(r'\s+', '-', text.lower().strip())) or 'section'


def resolve_source(source: str, href: str) -> str:
    return os.path.normpath(str(PurePosixPath(source).parent / unquote(href))).replace('\\', '/')


def navigation(specs: list[dict], current: str) -> str:
    groups: dict[str, list[dict]] = {}
    for spec in specs:
        groups.setdefault(spec['group'], []).append(spec)
    out = ['<a class="doc-home" href="../index.html">← BACK TO THE PROJECT</a>']
    for name, items in groups.items():
        out.append(f'<div class="doc-group">{html.escape(name)}</div>')
        for item in items:
            state = ' aria-current="page"' if item['slug'] == current else ''
            out.append(f'<a class="doc-link"{state} href="{item["slug"]}.html">{html.escape(item["title"])}</a>')
    return ''.join(out)


def render_document(text: str, source: str, mapping: dict[str, str]) -> tuple[str, list[tuple[str, str]]]:
    md = MarkdownIt('commonmark', {'html': False}).enable('table')
    tokens = md.parse(text)
    toc = []
    used: dict[str, int] = {}
    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            title = tokens[i + 1].content
            identity = slug(title)
            used[identity] = used.get(identity, 0) + 1
            if used[identity] > 1:
                identity += '-' + str(used[identity])
            token.attrSet('id', identity)
            if token.tag == 'h2':
                toc.append((identity, title))
        for child in token.children or []:
            if child.type != 'link_open':
                continue
            href = child.attrGet('href') or ''
            parts = urlsplit(href)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            target = resolve_source(source, parts.path)
            if target in mapping:
                child.attrSet('href', urlunsplit(('', '', mapping[target] + '.html', parts.query, parts.fragment)))
            else:
                from urllib.parse import quote
                child.attrSet('href', REPO + '/blob/main/' + quote(target, safe='/') + ('#' + parts.fragment if parts.fragment else ''))
    rendered = md.renderer.render(tokens, md.options, {})
    rendered = rendered.replace('<table>', '<div class="table-scroll"><table>').replace('</table>', '</table></div>')
    return rendered, toc


def document_shell(spec: dict, content: str, toc: list[tuple[str, str]], specs: list[dict]) -> str:
    title = html.escape(spec['title'])
    toc_html = ''.join(f'<a href="#{html.escape(i)}">{html.escape(t)}</a>' for i, t in toc)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — CafeRoomba documentation</title><meta name="description" content="{title}: CafeRoomba engineering documentation, evidence and limitations.">
<meta name="theme-color" content="#173b30"><link rel="canonical" href="{PUBLIC_URL}docs/{spec['slug']}.html">
<link rel="icon" href="../assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="../assets/style.css"><script src="../assets/site.js" defer></script></head>
<body><a class="skip-link" href="#main">Skip to content</a><header class="site-header"><div class="nav-shell">
<a class="brand" href="../index.html"><img src="../assets/favicon.svg" alt="" width="32" height="32">CafeRoomba<span class="brand-dot">/</span></a>
<nav aria-label="Main navigation"><a href="../index.html">The project</a><a href="index.html">Documentation</a><a class="nav-github" href="{REPO}">GitHub ↗</a></nav></div></header>
<div class="doc-shell"><button class="docs-menu-toggle" aria-controls="doc-navigation" aria-expanded="false">Browse documentation + </button>
<aside class="doc-sidebar" id="doc-navigation" aria-label="Documentation navigation">{navigation(specs,spec['slug'])}</aside>
<main class="doc-main" id="main"><div class="breadcrumb"><a href="index.html">ENGINEERING NOTEBOOK</a><span>/</span><span>{title}</span></div>{content}
<div class="doc-meta"><span>Independent project by Edwin Kestler.</span><a href="{REPO}/blob/main/{spec['source']}">View source on GitHub ↗</a></div></main>
<aside class="doc-toc" aria-label="On this page"><strong>ON THIS PAGE</strong>{toc_html}</aside></div>
<footer class="site-footer"><div class="wrap footer-grid"><div><a class="brand" href="../index.html">CafeRoomba /</a><p>Open-source field robotics. Documented evidence, explicit limits.</p></div><div class="footer-links"><a href="status.html">Status</a><a href="security.html">Security</a><a href="{REPO}/blob/main/LICENSE">License</a></div></div></footer></body></html>"""


def build(root: Path, output: Path) -> dict:
    root = root.resolve()
    if output.is_symlink():
        raise ValueError('Refusing symlink output')
    output = output.resolve()
    if output == root or output in root.parents or output.name != '_site':
        raise ValueError('Output must be a disposable directory named _site, not a source/parent directory')
    specs = json.loads((root / 'site/documents.json').read_text())
    mapping = {s['source']: s['slug'] for s in specs}
    if len(mapping) != len(specs) or len({s['slug'] for s in specs}) != len(specs):
        raise ValueError('Duplicate source or slug in document allowlist')
    if output.exists():
        shutil.rmtree(output)
    (output / 'assets').mkdir(parents=True)
    (output / 'docs').mkdir()
    copied=[]
    for name in ASSETS:
        source = root / 'site/assets' / name
        if source.is_symlink() or not source.is_file():
            raise ValueError(f'Missing or symlink public asset: {name}')
        shutil.copyfile(source, output / 'assets' / name)
        copied.append('assets/' + name)
    shutil.copyfile(root / 'site/index.html', output / 'index.html')
    for spec in specs:
        source = (root / spec['source']).resolve()
        if root not in source.parents or not source.is_file() or not re.fullmatch(r'[a-z0-9-]+', spec['slug']):
            raise ValueError('Invalid document allowlist entry')
        content, toc = render_document(source.read_text(), spec['source'], mapping)
        (output / 'docs' / (spec['slug'] + '.html')).write_text(document_shell(spec, content, toc, specs))
    (output / '.nojekyll').write_text('')
    (output / '404.html').write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Page not found — CafeRoomba</title></head><body style="font-family:system-ui;margin:10vh 8vw;color:#173b30;background:#f6f5ef"><h1>This path needs a course correction.</h1><p>The page is not available.</p><a href="{PUBLIC_URL}">Return to CafeRoomba →</a></body></html>""")
    urls = [PUBLIC_URL] + [PUBLIC_URL + 'docs/' + s['slug'] + '.html' for s in specs]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join('<url><loc>'+u+'</loc></url>' for u in urls) + '</urlset>'
    (output/'sitemap.xml').write_text(sitemap)
    (output/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+PUBLIC_URL+'sitemap.xml\n')
    report = {'documents':len(specs), 'assets':copied, 'robot_code_executed':False, 'private_bucket_accessed':False}
    (output/'build-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    print(json.dumps(build(args.root,args.output or args.root/'_site'),indent=2))
