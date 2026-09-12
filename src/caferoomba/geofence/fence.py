"""Metric patio geofence. Constructors are inert; load() performs file I/O.

Coordinates at the API boundary are latitude/longitude named arguments.
Geometry and paths use (longitude, latitude). Margin is metres, not degrees.
This companion check does not replace the independently configured Cube fence.
"""
from __future__ import annotations

import math
from pathlib import Path


class Fence:
    def __init__(self, *, required: bool, kml_path: str | Path | None = None,
                 region_name: str | None = None, exclusion_names: tuple[str, ...] = (),
                 clearance_m: float = 0.0, member: str | None = None) -> None:
        if not math.isfinite(clearance_m) or clearance_m < 0:
            raise ValueError("clearance_m must be finite and nonnegative")
        self.required, self.path = required, Path(kml_path) if kml_path else None
        self.region_name, self.exclusions = region_name, exclusion_names
        self.clearance_m, self.member = clearance_m, member
        self.region = self.safe_area = self.project = None

    def load(self) -> None:
        if self.path is None:
            if self.required:
                raise ValueError("required geofence has no map")
            return
        from pyproj import CRS, Transformer
        from shapely.ops import transform

        from caferoomba.geofence.kml import load_kml

        region = load_kml(self.path, region_name=self.region_name,
                          exclusion_names=self.exclusions, member=self.member)
        center = region.geometry.centroid
        local = CRS.from_proj4(f"+proj=aeqd +lat_0={center.y} +lon_0={center.x} "
                               "+datum=WGS84 +units=m +no_defs")
        project = Transformer.from_crs("EPSG:4326", local, always_xy=True)
        metric = transform(project.transform, region.geometry)
        safe_area = metric.buffer(-self.clearance_m) if self.clearance_m else metric
        if safe_area.is_empty or not safe_area.is_valid:
            raise ValueError("robot radius/margin leaves no allowed area")
        self.region, self.safe_area, self.project = region, safe_area, project

    @staticmethod
    def _valid(latitude_deg, longitude_deg) -> bool:
        return (latitude_deg is not None and longitude_deg is not None
                and math.isfinite(latitude_deg) and math.isfinite(longitude_deg)
                and -90 <= latitude_deg <= 90 and -180 <= longitude_deg <= 180)

    def allows(self, latitude_deg: float | None, longitude_deg: float | None) -> bool:
        if self.safe_area is None:
            return not self.required and self.path is None
        if not self._valid(latitude_deg, longitude_deg):
            return False
        from shapely.geometry import Point
        x, y = self.project.transform(longitude_deg, latitude_deg, errcheck=True)
        return bool(self.safe_area.covers(Point(x, y)))

    def allows_path(self, lon_lat: list[tuple[float, float]]) -> bool:
        """Check the complete center path inside a footprint-eroded safe region."""
        if not lon_lat or any(not self._valid(lat, lon) for lon, lat in lon_lat):
            return False
        if self.safe_area is None:
            return not self.required and self.path is None
        from shapely.geometry import LineString, Point
        points = [self.project.transform(lon, lat, errcheck=True) for lon, lat in lon_lat]
        geometry = Point(points[0]) if len(points) == 1 else LineString(points)
        return bool(self.safe_area.covers(geometry))

    def metadata(self) -> dict:
        return {"loaded": self.region is not None, "required": self.required,
                "source_sha256": self.region.source_sha256 if self.region else None,
                "region_name": self.region.region_name if self.region else None,
                "clearance_m": self.clearance_m}
