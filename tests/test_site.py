"""Publication checks; no robot imports or device access.

Install site/requirements.txt before running. Ordinary robot CI skips this
module when the isolated website renderer is absent.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import pytest
pytest.importorskip('markdown_it')
ROOT=Path(__file__).resolve().parents[1]


def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def test_build_and_internal_links(tmp_path):
    builder=load('build_site'); validator=load('check_site'); out=tmp_path/'_site'
    report=builder.build(ROOT,out)
    assert report['documents']>=20
    assert report['robot_code_executed'] is False
    assert validator.check(out)['errors']==[]
    assert not list(out.rglob('*.py'))
    assert 'prototype' in (out/'index.html').read_text()


def test_markdown_html_is_not_executable():
    builder=load('build_site')
    content,_=builder.render_document('<script>alert(1)</script>', 'docs/x.md', {})
    assert '<script>' not in content


def test_output_guard():
    builder=load('build_site')
    with pytest.raises(ValueError): builder.build(ROOT,ROOT)


def test_only_two_approved_videos_with_strict_budget():
    import hashlib
    import json
    manifest = json.loads((ROOT / 'site/media.json').read_text())
    assert len(manifest['clips']) == 2
    assert sum(clip['public_bytes'] for clip in manifest['clips']) < 9_000_000
    for clip in manifest['clips']:
        path = ROOT / 'site' / clip['public_asset']
        assert 0 < path.stat().st_size < 9_000_000
        assert path.stat().st_size == clip['public_bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == clip['public_sha256']
        assert clip['autonomy_evidence'] is False


def test_video_controls_and_accessible_diagrams():
    from html.parser import HTMLParser
    from xml.etree import ElementTree
    class MediaParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.videos = []
        def handle_starttag(self, tag, attrs):
            if tag == 'video':
                self.videos.append(dict(attrs))
    parser = MediaParser()
    text = (ROOT / 'site/index.html').read_text()
    parser.feed(text)
    assert len(parser.videos) == 2
    for video in parser.videos:
        assert {'autoplay', 'muted', 'loop', 'playsinline', 'controls', 'poster'} <= video.keys()
        assert video.get('aria-label')
    assert 'Google Cloud Colab Enterprise' in text
    assert 'id="experiment"' in text and 'id="physical-ai"' in text
    assert 'Perception → Reasoning → Learned Action → Navigation → Memory → Autonomy' in text
    for filename in ('training-pipeline.svg', 'physical-ai-cycle.svg'):
        svg = ElementTree.parse(ROOT / 'site/assets' / filename).getroot()
        assert svg.find('{http://www.w3.org/2000/svg}title') is not None
        assert svg.find('{http://www.w3.org/2000/svg}desc') is not None


def test_unapproved_video_rejected(tmp_path):
    out = tmp_path / '_site'
    load('build_site').build(ROOT, out)
    (out / 'assets/unapproved.mp4').write_bytes(b'not approved')
    with pytest.raises(ValueError, match='Unapproved/oversize video'):
        load('check_site').check(out)


def test_experiment_diagram_urls_are_rewritten(tmp_path):
    out = tmp_path / '_site'
    load('build_site').build(ROOT, out)
    html = (out / 'docs/experiment.html').read_text()
    assert 'src="../assets/training-pipeline.svg"' in html
    assert 'src="../assets/physical-ai-cycle.svg"' in html
