from __future__ import annotations

import json
import os
import socket
import threading
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Iterable

import folium
import qrcode
import qrcode.image.svg
from flask import Flask, Response, flash, jsonify, redirect, render_template, request, send_from_directory, url_for
from PIL import ExifTags, Image
from werkzeug.utils import secure_filename

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pillow_heif = None


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".tif", ".tiff", ".heic", ".heif"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 250 * 1024 * 1024


@dataclass(frozen=True)
class PhotoPoint:
    filename: str
    latitude: float
    longitude: float
    taken_at: datetime | None


@dataclass
class TrailState:
    points: list[PhotoPoint]
    routed_path: list[tuple[float, float]] = field(default_factory=list)
    map_html: str | None = None
    skipped: int = 0
    version: int = 0
    updated_at: datetime | None = None


trail_state = TrailState(points=[])
trail_lock = threading.Lock()


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return socket.gethostbyname(socket.gethostname())


def get_public_base_url() -> str:
    port = request.host.split(":")[-1] if ":" in request.host else "5000"
    return f"http://{get_local_ip()}:{port}"


def rational_to_float(value) -> float:
    if isinstance(value, tuple):
        numerator, denominator = value
        return float(numerator) / float(denominator)
    return float(value)


def dms_to_decimal(dms, ref: str) -> float:
    degrees = rational_to_float(dms[0])
    minutes = rational_to_float(dms[1])
    seconds = rational_to_float(dms[2])
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if ref in {"S", "W"}:
        decimal *= -1
    return decimal


def get_exif(image: Image.Image) -> dict:
    raw_exif = image.getexif()
    if not raw_exif:
        return {}

    exif = {}
    for tag_id, value in raw_exif.items():
        tag_name = ExifTags.TAGS.get(tag_id, tag_id)
        exif[tag_name] = value

    gps_ifd = raw_exif.get_ifd(ExifTags.IFD.GPSInfo)
    if gps_ifd:
        exif["GPSInfo"] = {
            ExifTags.GPSTAGS.get(gps_id, gps_id): gps_value
            for gps_id, gps_value in gps_ifd.items()
        }

    exif_ifd = raw_exif.get_ifd(ExifTags.IFD.Exif)
    for tag_id, value in exif_ifd.items():
        tag_name = ExifTags.TAGS.get(tag_id, tag_id)
        exif[tag_name] = value

    return exif


def parse_timestamp(exif: dict) -> datetime | None:
    for key in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
        value = exif.get(key)
        if not value:
            continue
        try:
            return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
        except ValueError:
            continue
    return None


def extract_photo_point(path: Path) -> PhotoPoint | None:
    with Image.open(path) as image:
        exif = get_exif(image)

    gps = exif.get("GPSInfo") or {}
    required = ("GPSLatitude", "GPSLatitudeRef", "GPSLongitude", "GPSLongitudeRef")
    if not all(key in gps for key in required):
        return None

    latitude = dms_to_decimal(gps["GPSLatitude"], gps["GPSLatitudeRef"])
    longitude = dms_to_decimal(gps["GPSLongitude"], gps["GPSLongitudeRef"])
    taken_at = parse_timestamp(exif)

    return PhotoPoint(
        filename=path.name,
        latitude=latitude,
        longitude=longitude,
        taken_at=taken_at,
    )


def save_uploaded_files(files: Iterable) -> list[Path]:
    saved_paths = []
    for file in files:
        if not file or not file.filename:
            continue
        if not allowed_file(file.filename):
            continue

        original = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{original}"
        destination = UPLOAD_DIR / unique_name
        file.save(destination)
        saved_paths.append(destination)
    return saved_paths


def get_routed_polyline(points: list[PhotoPoint]) -> list[tuple[float, float]]:
    coords = ";".join(f"{p.longitude},{p.latitude}" for p in points)
    url = f"http://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"
    try:
        with urllib.request.urlopen(url, timeout=6) as resp:
            data = json.loads(resp.read())
        if data.get("code") == "Ok" and data["routes"]:
            return [(c[1], c[0]) for c in data["routes"][0]["geometry"]["coordinates"]]
    except Exception:
        pass
    return [(p.latitude, p.longitude) for p in points]


def distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    r_lat1 = radians(lat1)
    r_lat2 = radians(lat2)
    h = sin(d_lat / 2) ** 2 + cos(r_lat1) * cos(r_lat2) * sin(d_lon / 2) ** 2
    return 2 * 6371 * asin(sqrt(h))


def route_distance_km(path: list[tuple[float, float]]) -> float:
    if len(path) < 2:
        return 0.0
    return sum(distance_km(path[i], path[i + 1]) for i in range(len(path) - 1))


def photo_path(points: list[PhotoPoint]) -> list[tuple[float, float]]:
    return [(p.latitude, p.longitude) for p in points]


def display_distance_km(points: list[PhotoPoint], routed: list[tuple[float, float]]) -> float:
    direct_distance = route_distance_km(photo_path(points))
    routed_distance = route_distance_km(routed)
    if not routed:
        return direct_distance
    if direct_distance <= 0:
        return routed_distance
    # OSRM can occasionally return a wildly circuitous polyline for demo data or
    # bad coordinate sequences. Prefer the photo-to-photo distance when routing
    # is clearly implausible, instead of showing a scary fake-looking total.
    if routed_distance > direct_distance * 3.5:
        return direct_distance
    return routed_distance


def build_trip_stats(points: list[PhotoPoint], routed: list[tuple[float, float]], skipped: int) -> dict:
    timestamps = [point.taken_at for point in points if point.taken_at]
    start = min(timestamps) if timestamps else None
    end = max(timestamps) if timestamps else None
    duration = end - start if start and end else None
    distance = display_distance_km(points, routed)
    return {
        "photo_count": len(points),
        "skipped_count": skipped,
        "distance_miles": format_miles(distance * 0.621371),
        "avg_miles": format_miles((distance * 0.621371) / max(1, len(points) - 1)),
        "distance_km": round(distance, 1),
        "start_label": start.strftime("%b %d, %Y %H:%M") if start else "Unknown start",
        "end_label": end.strftime("%b %d, %Y %H:%M") if end else "Unknown end",
        "duration_label": format_duration(duration.total_seconds()) if duration else "Unknown duration",
    }


def format_miles(miles: float) -> str:
    if miles < 10:
        return f"{miles:.1f}"
    return f"{round(miles):,}"


def format_duration(total_seconds: float) -> str:
    minutes = int(total_seconds // 60)
    if minutes < 60:
        return f"{minutes} min"
    hours, mins = divmod(minutes, 60)
    if hours < 24:
        return f"{hours} hr {mins} min"
    days, hours = divmod(hours, 24)
    return f"{days} d {hours} hr"


def create_map(points: list[PhotoPoint], routed: list[tuple[float, float]]) -> str | None:
    if not points:
        return None

    center = [
        sum(point.latitude for point in points) / len(points),
        sum(point.longitude for point in points) / len(points),
    ]
    trail_map = folium.Map(
        location=center,
        zoom_start=14,
        control_scale=True,
        tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    )

    if routed:
        folium.PolyLine(
            routed,
            color="#4da6ff",
            weight=5,
            opacity=0.9,
        ).add_to(trail_map)

    for index, point in enumerate(points, start=1):
        folium.Marker(
            location=[point.latitude, point.longitude],
            icon=folium.Icon(color="blue" if index < len(points) else "green", icon="camera"),
        ).add_to(trail_map)

    bounds = [[point.latitude, point.longitude] for point in points]
    trail_map.fit_bounds(bounds, padding=(32, 32))
    return trail_map.get_root().render()


def build_trail(points: list[PhotoPoint]) -> tuple[list[tuple[float, float]], str | None]:
    """Compute routed path + map HTML once. Called on upload/dev, not on every GET."""
    routed = get_routed_polyline(points) if len(points) > 1 else []
    map_html = create_map(points, routed)
    return routed, map_html


def process_uploaded_photos(files: Iterable) -> tuple[list[PhotoPoint], int, bool]:
    points: list[PhotoPoint] = []
    skipped = 0
    saved_paths = save_uploaded_files(files)

    if not saved_paths:
        return points, skipped, False

    for path in saved_paths:
        try:
            point = extract_photo_point(path)
        except Exception:
            point = None
        if point:
            points.append(point)
        else:
            skipped += 1

    points.sort(key=lambda point: point.taken_at or datetime.min)
    return points, skipped, True


def update_trail_state(
    points: list[PhotoPoint],
    skipped: int,
    routed: list[tuple[float, float]],
    map_html: str | None,
) -> int:
    with trail_lock:
        trail_state.points = points
        trail_state.routed_path = routed
        trail_state.map_html = map_html
        trail_state.skipped = skipped
        trail_state.version += 1
        trail_state.updated_at = datetime.now()
        return trail_state.version


def get_trail_state() -> TrailState:
    with trail_lock:
        return TrailState(
            points=list(trail_state.points),
            routed_path=list(trail_state.routed_path),
            map_html=trail_state.map_html,
            skipped=trail_state.skipped,
            version=trail_state.version,
            updated_at=trail_state.updated_at,
        )


_US_CITIES = [
    (47.6062, -122.3321), (45.5051, -122.6750), (37.7749, -122.4194),
    (34.0522, -118.2437), (32.7157, -117.1611), (36.1699, -115.1398),
    (33.4484, -112.0740), (32.2540, -110.9742), (35.0853, -106.6511),
    (35.6870, -105.9378), (31.7619, -106.4850), (39.7392, -104.9903),
    (38.8339, -104.8214), (40.7608, -111.8910), (43.6187, -116.2146),
    (46.8797, -113.9966), (45.7833, -108.5007), (43.5978, -110.6531),
    (44.0805, -103.2310), (46.8772, -96.7898),  (44.9778, -93.2650),
    (43.0731, -89.4012),  (41.8781, -87.6298),  (39.7684, -86.1581),
    (39.0997, -94.5786),  (38.5767, -92.1735),  (36.1540, -95.9928),
    (35.4676, -97.5164),  (29.7604, -95.3698),  (30.2672, -97.7431),
    (32.7767, -96.7970),  (29.4241, -98.4936),  (38.2527, -85.7585),
    (36.1627, -86.7816),  (35.1495, -90.0490),  (29.9511, -90.0715),
    (30.3322, -81.6557),  (27.9506, -82.4572),  (33.7490, -84.3880),
    (35.2271, -80.8431),  (35.7796, -78.6382),  (37.5407, -77.4360),
    (38.9072, -77.0369),  (39.2904, -76.6122),  (39.9526, -75.1652),
    (40.7128, -74.0060),  (41.7658, -72.6734),  (42.3601, -71.0589),
    (41.2565, -95.9345),  (43.5460, -96.7313),
]


def nearest_neighbor_order(coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(coords) < 3:
        return coords
    remaining = coords[:]
    ordered = [remaining.pop(0)]
    while remaining:
        current = ordered[-1]
        next_index = min(
            range(len(remaining)),
            key=lambda i: distance_km(current, remaining[i]),
        )
        ordered.append(remaining.pop(next_index))
    return ordered


@app.route("/dev/random-map", methods=["POST"])
def dev_random_map():
    import random
    from datetime import timedelta

    anchor = random.choice(_US_CITIES)
    count = random.randint(6, 12)
    selected = []
    lat, lon = anchor
    for _ in range(count):
        lat += random.uniform(-0.16, 0.16)
        lon += random.uniform(-0.16, 0.16)
        selected.append((lat, lon))

    t = datetime(2024, 7, 4, 9, 0, 0)
    points = []
    for i, (lat, lon) in enumerate(selected):
        points.append(PhotoPoint(
            filename=f"dev_{i+1:02d}.jpg",
            latitude=round(lat + random.uniform(-0.06, 0.06), 6),
            longitude=round(lon + random.uniform(-0.06, 0.06), 6),
            taken_at=t,
        ))
        t += timedelta(minutes=random.randint(25, 120))

    routed, map_html = build_trail(points)
    update_trail_state(points, skipped=0, routed=routed, map_html=map_html)
    return redirect(url_for("index"))


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/reset", methods=["POST"])
def reset():
    update_trail_state(points=[], skipped=0, routed=[], map_html=None)
    return redirect(url_for("index"))


@app.route("/qr.svg")
def qr_code():
    target_url = get_public_base_url()
    image = qrcode.make(
        target_url,
        image_factory=qrcode.image.svg.SvgPathImage,
        box_size=14,
        border=2,
    )
    buffer = BytesIO()
    image.save(buffer)
    return Response(buffer.getvalue(), mimetype="image/svg+xml")


@app.route("/trail-state")
def trail_state_status():
    state = get_trail_state()
    return jsonify(
        {
            "version": state.version,
            "photo_count": len(state.points),
            "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        }
    )


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        points, skipped, had_uploads = process_uploaded_photos(request.files.getlist("photos"))

        if not had_uploads:
            flash("Upload JPG, TIFF, HEIC, or HEIF photos with GPS metadata.")
            return redirect(url_for("index"))

        if not points:
            flash("No GPS coordinates were found in those photos.")
            return redirect(url_for("index"))

        routed, map_html = build_trail(points)
        update_trail_state(points, skipped, routed=routed, map_html=map_html)
        return redirect(url_for("index"))

    state = get_trail_state()
    return render_template(
        "index.html",
        points=state.points,
        points_json=[{
            "lat": p.latitude,
            "lon": p.longitude,
            "filename": p.filename,
            "taken_at": p.taken_at.strftime("%b %d, %Y  %H:%M") if p.taken_at else None,
        } for p in state.points],
        routed_json=state.routed_path,
        skipped=state.skipped,
        map_html=state.map_html,
        trip_stats=build_trip_stats(state.points, state.routed_path, state.skipped),
        phone_upload_url=get_public_base_url(),
        trail_version=state.version,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False)
