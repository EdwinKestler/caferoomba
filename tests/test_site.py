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
