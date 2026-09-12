"""Bounded KML/KMZ loading with explicit region selection.

Pure file/geometry code: no hardware or network. Public coordinates are
(longitude, latitude), never (latitude, longitude). DTDs, entities, network
links, invalid rings, and ambiguous maps are rejected rather than repaired.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from lxml import etree
from pykml import parser as kml_parser
from shapely.geometry import Polygon
from shapely.ops import unary_union

NS = {"k": "http://www.opengis.net/kml/2.2"}
MAX_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class KmlRegion:
    """Validated WGS84 geometry and provenance; geometry includes holes."""
    geometry: object
    source_sha256: str
    region_name: str
    exclusions: tuple[str, ...]


def _read(path: Path, member: str | None) -> bytes:
    if path.suffix.lower() == ".kml":
        if path.stat().st_size > MAX_BYTES:
            raise ValueError("KML exceeds size limit")
        return path.read_bytes()
    if path.suffix.lower() != ".kmz":
        raise ValueError("map must be .kml or .kmz")
    if path.stat().st_size > 16 * MAX_BYTES:
        raise ValueError("KMZ exceeds archive size limit")
    with ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > 128 or sum(i.file_size for i in infos) > 16 * MAX_BYTES:
            raise ValueError("KMZ exceeds expanded size/member limit")
        if any(".." in PurePosixPath(i.filename).parts or i.filename.startswith("/")
               for i in infos):
            raise ValueError("unsafe KMZ member path")
        candidates = [i for i in infos if i.filename.lower().endswith(".kml")]
        selected = [i for i in candidates if i.filename == member] if member else candidates
        if len(selected) != 1:
            raise ValueError("select exactly one KML member in KMZ")
        info = selected[0]
        if info.file_size > MAX_BYTES:
            raise ValueError("KML member exceeds size limit")
        with archive.open(info) as handle:
            data = handle.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("expanded KML exceeds size limit")
        return data


def _ring(element) -> list[tuple[float, float]]:
    text = " ".join(element.itertext())
    tokens = text.split()
    if not 4 <= len(tokens) <= 10000:
        raise ValueError("a ring requires 4..10000 coordinate tuples")
    result = []
    for token in tokens:
        values = [float(x) for x in token.split(",")]
        if len(values) not in (2, 3) or not all(math.isfinite(x) for x in values):
            raise ValueError("invalid coordinate tuple")
        lon, lat = values[:2]
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError("KML coordinates must be longitude,latitude")
        result.append((lon, lat))
    if result[0] != result[-1] or len(set(result[:-1])) < 3:
        raise ValueError("KML ring must be closed with three distinct vertices")
    return result


def load_kml(path: Path, *, region_name: str | None = None,
             exclusion_names: tuple[str, ...] = (), member: str | None = None) -> KmlRegion:
    """Load one named Placemark (MultiGeometry supported) and subtract exclusions.

    Unnamed single regions are permitted. Multiple candidate inclusion regions
    require an explicit name/id. No polygon is silently repaired with buffer(0).
    """
    data = _read(Path(path), member)
    safe = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False,
                           recover=False, huge_tree=False)
    root = etree.fromstring(data, parser=safe)
    if root.getroottree().docinfo.doctype or any(isinstance(n, etree._Entity) for n in root.iter()):
        raise ValueError("DTD/entity maps are forbidden")
    if root.xpath(".//k:NetworkLink", namespaces=NS):
        raise ValueError("NetworkLink maps must be made local and explicit")
    # Feed only the sanitized, DTD-free tree to the legacy pykml parser.
    root = kml_parser.fromstring(etree.tostring(root))
    features = {}
    for index, placemark in enumerate(root.xpath(".//k:Placemark", namespaces=NS)):
        nodes = placemark.xpath(".//k:Polygon", namespaces=NS)
        if not nodes:
            continue
        name = (
            placemark.findtext("k:name", namespaces=NS)
            or placemark.get("id")
            or f"region-{index}"
        )
        if name in features:
            raise ValueError("duplicate region name/id")
        polygons = []
        for node in nodes:
            outer = node.xpath("./k:outerBoundaryIs/k:LinearRing/k:coordinates", namespaces=NS)
            if len(outer) != 1:
                raise ValueError("polygon requires one outer ring")
            holes = node.xpath("./k:innerBoundaryIs/k:LinearRing/k:coordinates", namespaces=NS)
            polygon = Polygon(_ring(outer[0]), [_ring(hole) for hole in holes])
            if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
                raise ValueError("invalid/self-intersecting polygon")
            polygons.append(polygon)
        features[str(name)] = unary_union(polygons)
    if any(name not in features for name in exclusion_names):
        raise ValueError("requested exclusion region is missing")
    names = [name for name in features if name not in exclusion_names]
    if region_name is None:
        if len(names) != 1:
            raise ValueError("map is empty or ambiguous; select a region_name")
        region_name = names[0]
    if region_name not in names:
        raise ValueError("selected inclusion region is missing or excluded")
    geometry = features[region_name]
    if exclusion_names:
        geometry = geometry.difference(unary_union([features[n] for n in exclusion_names]))
    if geometry.is_empty or not geometry.is_valid:
        raise ValueError("no valid allowed area remains")
    xmin, ymin, xmax, ymax = geometry.bounds
    if xmax - xmin > 0.5 or ymax - ymin > 0.5:
        raise ValueError("map is not a local patio region")
    return KmlRegion(geometry, hashlib.sha256(data).hexdigest(), region_name, exclusion_names)
