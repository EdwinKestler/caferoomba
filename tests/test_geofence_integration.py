"""Synthetic geographic fixtures; never represent a real patio authorization."""
from zipfile import ZipFile
import pytest
from caferoomba.geofence.fence import Fence
from caferoomba.geofence.kml import load_kml


def ring(points):
    return " ".join(f"{-90+x},{14+y},0" for x, y in points)


def placemark(name, outer, hole=None):
    text = (f'<Placemark><name>{name}</name><Polygon><outerBoundaryIs><LinearRing>'
            f'<coordinates>{ring(outer)}</coordinates></LinearRing></outerBoundaryIs>')
    if hole:
        text += ('<innerBoundaryIs><LinearRing><coordinates>' + ring(hole)
                 + '</coordinates></LinearRing></innerBoundaryIs>')
    return text + '</Polygon></Placemark>'


OUTER = [(0, 0), (.001, 0), (.001, .001), (0, .001), (0, 0)]
HOLE = [(.0004, .0004), (.0006, .0004), (.0006, .0006), (.0004, .0006), (.0004, .0004)]


def document(content):
    return '<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Folder>' + content + '</Folder></Document></kml>'


def write_map(tmp_path, content=None):
    path = tmp_path / 'map.kml'
    path.write_text(document(content or placemark('patio', OUTER, HOLE)))
    return path


def test_lon_lat_holes_metric_margin_and_outside(tmp_path):
    fence = Fence(required=True, kml_path=write_map(tmp_path), clearance_m=3)
    fence.load()
    assert fence.allows(14.0002, -89.9998)
    assert not fence.allows(14.0005, -89.9995)  # Hole, not a safe coffee patch.
    assert not fence.allows(14.002, -89.9995)
    assert not fence.allows(14.000001, -89.9998)  # Within 3 m of edge.
    assert not fence.allows(None, -90)
    assert not fence.allows(float('nan'), -90)
    assert fence.metadata()['source_sha256']


def test_complete_path_rejects_crossing_hole(tmp_path):
    fence = Fence(required=True, kml_path=write_map(tmp_path))
    fence.load()
    points = [(-89.9998, 14.0005), (-89.9992, 14.0005)]
    assert all(fence.allows(lat, lon) for lon, lat in points)
    assert not fence.allows_path(points)
    assert fence.allows_path([(-89.9998, 14.0002), (-89.9992, 14.0002)])


def test_required_missing_or_unloaded_is_closed(tmp_path):
    assert not Fence(required=True).allows(14, -90)
    with pytest.raises(ValueError):
        Fence(required=True).load()
    with pytest.raises(FileNotFoundError):
        Fence(required=True, kml_path=tmp_path / 'absent.kml').load()
    assert Fence(required=False).allows(None, None)  # Explicit simulation/diagnostic configuration.


def test_ambiguous_regions_require_selection(tmp_path):
    path = write_map(tmp_path, placemark('a', OUTER) + placemark('b', HOLE))
    with pytest.raises(ValueError, match='ambiguous'):
        load_kml(path)
    selected = load_kml(path, region_name='a', exclusion_names=('b',))
    assert selected.exclusions == ('b',)
    with pytest.raises(ValueError):
        load_kml(path, region_name='a', exclusion_names=('missing',))


def test_kmz_ignores_non_kml_first_entry(tmp_path):
    path = tmp_path / 'map.kmz'
    with ZipFile(path, 'w') as archive:
        archive.writestr('icon.png', b'not an image')
        archive.writestr('nested/doc.kml', document(placemark('patio', OUTER)))
    assert load_kml(path).region_name == 'patio'
    with ZipFile(path, 'a') as archive:
        archive.writestr('other.kml', document(placemark('other', OUTER)))
    with pytest.raises(ValueError, match='exactly one'):
        load_kml(path)
    assert load_kml(path, member='nested/doc.kml').region_name == 'patio'


def test_dtd_and_self_intersection_rejected(tmp_path):
    path = tmp_path / 'unsafe.kml'
    path.write_text('<!DOCTYPE kml [<!ENTITY x "bad">]>' + document(placemark('patio', OUTER)))
    with pytest.raises(ValueError, match='DTD'):
        load_kml(path)
    bowtie = [(0, 0), (.001, .001), (.001, 0), (0, .001), (0, 0)]
    with pytest.raises(ValueError, match='invalid'):
        load_kml(write_map(tmp_path, placemark('bowtie', bowtie)))


def test_no_unclosed_ring_or_excessive_margin(tmp_path):
    with pytest.raises(ValueError, match='closed'):
        load_kml(write_map(tmp_path, placemark('bad', OUTER[:-1])))
    with pytest.raises(ValueError, match='no allowed area'):
        Fence(required=True, kml_path=write_map(tmp_path), clearance_m=1000).load()
