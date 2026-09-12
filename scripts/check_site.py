#!/usr/bin/env python3
"""Validate all local generated HTML links/assets without network or robot I/O."""
from __future__ import annotations
import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs=[]; self.ids=set(); self.duplicates=[]; self.h1=0; self.lang=False; self.missing_alt=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='html': self.lang=bool(a.get('lang'))
        if tag=='h1': self.h1+=1
        if tag=='img' and 'alt' not in a: self.missing_alt+=1
        if 'id' in a:
            if a['id'] in self.ids: self.duplicates.append(a['id'])
            self.ids.add(a['id'])
        if tag=='a' and a.get('href'): self.refs.append(a['href'])
        if tag in ('img','script','source','video') and a.get('src'): self.refs.append(a['src'])
        if tag=='video' and a.get('poster'): self.refs.append(a['poster'])
        if tag=='link' and a.get('rel') in ('stylesheet','icon') and a.get('href'): self.refs.append(a['href'])


def check(root: Path) -> dict:
    root=root.resolve(); pages={}; errors=[]; links=0
    for path in root.rglob('*.html'):
        parser=Page(); parser.feed(path.read_text()); pages[path.resolve()]=parser
        if not parser.lang or parser.h1!=1 or parser.missing_alt or parser.duplicates:
            errors.append(f'{path.relative_to(root)}: language/h1/alt/duplicate-id contract failed')
    if len(pages)<20: errors.append('Documentation build incomplete')
    for path,page in pages.items():
        for ref in page.refs:
            u=urlsplit(ref)
            if u.scheme or u.netloc: continue
            if u.path.startswith('/'): errors.append(f'Root-relative link may break project path: {ref}'); continue
            target=(path.parent/unquote(u.path)).resolve() if u.path else path
            if target.is_dir(): target=target/'index.html'
            links+=1
            if root not in target.parents or not target.exists():
                errors.append(f'{path.relative_to(root)} -> missing/escaping {ref}'); continue
            if u.fragment and target.suffix=='.html' and unquote(u.fragment) not in pages[target].ids:
                errors.append(f'{path.relative_to(root)} -> missing fragment {ref}')
    allowed_videos = {'assets/fpv-sample.mp4', 'assets/external-sample.mp4'}
    for path in root.rglob('*.mp4'):
        if str(path.relative_to(root)) not in allowed_videos or path.stat().st_size >= 9_000_000:
            errors.append('Unapproved/oversize video: '+str(path.relative_to(root)))
    for path in root.rglob('*'):
        if path.is_file() and (path.is_symlink() or path.suffix in {'.py','.env','.sqlite3','.pt','.onnx','.pem','.key'}):
            errors.append('Forbidden published file: '+str(path.relative_to(root)))
    report={'html_pages':len(pages),'local_references_checked':links,'errors':errors}
    if errors: raise ValueError(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]/'_site')
    print(json.dumps(check(p.parse_args().root),indent=2))
