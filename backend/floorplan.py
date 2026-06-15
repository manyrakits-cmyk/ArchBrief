"""
floorplan.py — ArchBrief Fáze 5: generátor schematického půdorysu

Pipeline: intent_model → spatial graph → geometry (zónové pásy) → SVG string
"""
from __future__ import annotations

from dataclasses import dataclass

# ── Konstanty ─────────────────────────────────────────────────────────────────

CANVAS_W = 800.0
PADDING = 20.0
AVAILABLE_W = CANVAS_W - 2 * PADDING   # 760.0

BAND_HEIGHTS: dict[str, float] = {
    "private": 130.0,
    "shared":  160.0,
    "public":  100.0,
}
ZONE_ORDER = ["private", "shared", "public"]   # top → bottom v SVG
MIN_ROOM_W = 80.0

ZONE_COLORS: dict[str, str] = {
    "public":  "#E8E8E8",
    "shared":  "#D4E8D4",
    "private": "#D4E0F0",
}

ROOM_NAMES: dict[str, str] = {
    # České klíče
    "obyvaci_pokoj":    "Obývací pokoj",
    "kuchyne":          "Kuchyně",
    "loznice":          "Ložnice",
    "detsky_pokoj":     "Dětský pokoj",
    "koupelna":         "Koupelna",
    "wc":               "WC",
    "pracovna":         "Pracovna",
    "garaz":            "Garáž",
    "terasa":           "Terasa",
    "zahrada":          "Zahrada",
    "chodba":           "Chodba",
    "satna":            "Šatna",
    "jidelna":          "Jídelna",
    "sklep":            "Sklep",
    "puda":             "Půda",
    "schodiste":        "Schodiště",
    "balkon":           "Balkon",
    "spiz":             "Spíž",
    "pokoj_pro_hosty":  "Pokoj pro hosty",
    "hobby_mistnost":   "Hobby místnost",
    "zadneri":          "Zádveří",
    "technická_mistnost": "Technická místnost",
    # Anglické ekvivalenty
    "living":           "Obývací pokoj",
    "kitchen":          "Kuchyně",
    "bedroom":          "Ložnice",
    "bedroom_master":   "Ložnice rodičů",
    "bathroom":         "Koupelna",
    "hall":             "Hala",
    "entry":            "Zádveří",
    "dining":           "Jídelna",
    "office":           "Pracovna",
    "garage":           "Garáž",
    "terrace":          "Terasa",
    "garden":           "Zahrada",
    "storage":          "Sklad",
    "laundry":          "Prádelna",
    "utility":          "Technická místnost",
}

ZONE_MAP: dict[str, str] = {
    # public
    "garaz": "public", "terasa": "public", "zahrada": "public",
    "chodba": "public", "garage": "public", "terrace": "public",
    "garden": "public", "hall": "public", "entry": "public",
    "zadneri": "public",
    # shared
    "obyvaci_pokoj": "shared", "kuchyne": "shared", "jidelna": "shared",
    "wc": "shared", "schodiste": "shared", "spiz": "shared",
    "living": "shared", "kitchen": "shared", "dining": "shared",
    "technická_mistnost": "shared", "utility": "shared",
    "laundry": "shared",
    # private
    "loznice": "private", "detsky_pokoj": "private", "koupelna": "private",
    "pracovna": "private", "satna": "private", "sklep": "private",
    "puda": "private", "balkon": "private", "pokoj_pro_hosty": "private",
    "hobby_mistnost": "private",
    "bedroom": "private", "bedroom_master": "private",
    "bathroom": "private", "office": "private",
    "storage": "private",
}


# ── Pomocné funkce ─────────────────────────────────────────────────────────────

def _normalize_key(s: str) -> str:
    key = s.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
    while "__" in key:
        key = key.replace("__", "_")
    return key.strip("_")


def _infer_zone(name_lower: str) -> str:
    """Záložní inference zóny z podřetězců v názvu."""
    if any(w in name_lower for w in (
        "ložnic", "loznic", "dětsk", "detsk",
        "koupeln", "pracov", "šatn", "satna",
        "balkon", "bedroom", "bathroom", "office",
        "pokoj pro host",
    )):
        return "private"
    if any(w in name_lower for w in (
        "obývac", "obyvac", "kuchyn", "jídeln", "jideln",
        "schodišt", "schodist", "spíž", "spiz",
        "technick", "living", "kitchen", "dining", "prádelna",
    )):
        return "shared"
    return "public"


def _capitalize_first(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _escape_xml(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


# ── Dataclassy ────────────────────────────────────────────────────────────────

@dataclass
class RoomRect:
    id: str
    name: str
    zone: str
    area_target: float
    x: float
    y: float
    width: float
    height: float


@dataclass
class FloorplanLayout:
    rooms: list[RoomRect]
    total_width: float
    total_height: float


# ── Spatial graph ──────────────────────────────────────────────────────────────

def build_spatial_graph(intent_model: dict) -> tuple[list[dict], list[dict]]:
    """
    Sestaví spatial graph (nodes + edges) z intent_model.program.
    Spaces mohou být dict {name, note, ...} nebo plain stringy.
    """
    program = (intent_model or {}).get("program") or {}
    raw_spaces = program.get("spaces") or []
    raw_relationships = program.get("relationships") or []

    nodes: list[dict] = []
    for space in raw_spaces:
        if isinstance(space, dict):
            raw_name = (space.get("name") or "").strip()
        else:
            raw_name = str(space).strip()
        if not raw_name:
            continue

        key = _normalize_key(raw_name)
        display_name = ROOM_NAMES.get(key) or _capitalize_first(raw_name)
        zone = ZONE_MAP.get(key) or _infer_zone(raw_name.lower())

        area_target = 15.0
        if isinstance(space, dict):
            raw_area = space.get("area_target") or space.get("area")
            if raw_area is not None:
                try:
                    area_target = float(raw_area)
                except (ValueError, TypeError):
                    pass

        nodes.append({
            "id": key,
            "raw_name": raw_name,
            "display_name": display_name,
            "zone": zone,
            "area_target": area_target,
        })

    # Deduplicita — zachovat první výskyt
    seen: set[str] = set()
    unique_nodes: list[dict] = []
    for n in nodes:
        if n["id"] not in seen:
            seen.add(n["id"])
            unique_nodes.append(n)

    # Edges
    edges: list[dict] = []
    for rel in raw_relationships:
        if not isinstance(rel, dict):
            continue
        from_raw = (rel.get("from") or "").strip()
        to_raw = (rel.get("to") or "").strip()
        rel_type = (rel.get("type") or "buffered").strip().lower()
        if not from_raw or not to_raw:
            continue
        if rel_type not in ("direct", "buffered", "visual"):
            rel_type = "buffered"   # české hodnoty → buffered
        edges.append({
            "from": _normalize_key(from_raw),
            "to":   _normalize_key(to_raw),
            "type": rel_type,
        })

    return unique_nodes, edges


# ── Geometry engine ────────────────────────────────────────────────────────────

def compute_layout(nodes: list[dict], edges: list[dict]) -> FloorplanLayout:
    """Rozloží místnosti do zónových pásů (private nahoře, public dole)."""
    zones: dict[str, list[dict]] = {"private": [], "shared": [], "public": []}
    for n in nodes:
        z = n["zone"] if n["zone"] in zones else "shared"
        zones[z].append(n)

    active_zones = [z for z in ZONE_ORDER if zones[z]]
    total_h = PADDING + sum(BAND_HEIGHTS[z] for z in active_zones) + PADDING

    rooms: list[RoomRect] = []
    current_y = PADDING

    for zone in active_zones:
        zone_nodes = zones[zone]
        band_h = BAND_HEIGHTS[zone]
        zone_total_area = sum(n["area_target"] for n in zone_nodes) or 1.0

        current_x = PADDING
        for n in zone_nodes:
            raw_w = (n["area_target"] / zone_total_area) * AVAILABLE_W
            room_w = max(MIN_ROOM_W, raw_w)
            rooms.append(RoomRect(
                id=n["id"],
                name=n["display_name"],
                zone=zone,
                area_target=n["area_target"],
                x=current_x,
                y=current_y,
                width=room_w,
                height=band_h,
            ))
            current_x += room_w

        current_y += band_h

    return FloorplanLayout(rooms=rooms, total_width=CANVAS_W, total_height=total_h)


# ── SVG generátor ──────────────────────────────────────────────────────────────

def _placeholder_svg() -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 120" '
        'width="400" height="120" font-family="sans-serif">'
        '<rect width="400" height="120" fill="#f5f5f5" rx="8"/>'
        '<text x="200" y="55" text-anchor="middle" font-size="13" fill="#bbb">'
        'Půdorys</text>'
        '<text x="200" y="75" text-anchor="middle" font-size="10" fill="#ccc">'
        'Popište místnosti pro zobrazení půdorysu</text>'
        '</svg>'
    )


def generate_svg(layout: FloorplanLayout, edges: list[dict]) -> str:
    if len(layout.rooms) < 2:
        return _placeholder_svg()

    w = layout.total_width
    h = layout.total_height
    room_lookup: dict[str, RoomRect] = {r.id: r for r in layout.rooms}
    lines: list[str] = []

    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {w:.0f} {h:.0f}" '
        f'width="{w:.0f}" height="{h:.0f}" '
        f'font-family="sans-serif">'
    )

    # Místnosti
    for room in layout.rooms:
        color = ZONE_COLORS.get(room.zone, "#E8E8E8")
        lines.append(
            f'  <rect x="{room.x:.1f}" y="{room.y:.1f}" '
            f'width="{room.width:.1f}" height="{room.height:.1f}" '
            f'fill="{color}" stroke="#999" stroke-width="1"/>'
        )
        cx = room.x + room.width / 2
        cy = room.y + room.height / 2
        lines.append(
            f'  <text x="{cx:.1f}" y="{cy - 8:.1f}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-size="11" font-weight="bold" fill="#333">'
            f'{_escape_xml(room.name)}</text>'
        )
        lines.append(
            f'  <text x="{cx:.1f}" y="{cy + 10:.1f}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-size="9" fill="#666">'
            f'{room.area_target:.0f} m²</text>'
        )

    # Vztahy
    for edge in edges:
        fr = room_lookup.get(edge["from"])
        to = room_lookup.get(edge["to"])
        if fr is None or to is None:
            continue
        fx = fr.x + fr.width / 2
        fy = fr.y + fr.height / 2
        tx = to.x + to.width / 2
        ty = to.y + to.height / 2
        if edge["type"] == "direct":
            stroke_attrs = 'stroke="#555" stroke-width="2"'
        elif edge["type"] == "visual":
            stroke_attrs = 'stroke="#aaa" stroke-width="1.5" stroke-dasharray="2,4"'
        else:
            stroke_attrs = 'stroke="#888" stroke-width="1.5" stroke-dasharray="8,4"'
        lines.append(
            f'  <line x1="{fx:.1f}" y1="{fy:.1f}" '
            f'x2="{tx:.1f}" y2="{ty:.1f}" '
            f'{stroke_attrs} opacity="0.6"/>'
        )

    # Celková plocha
    total_area = sum(r.area_target for r in layout.rooms)
    lines.append(
        f'  <text x="{w / 2:.1f}" y="{h - 6:.1f}" '
        f'text-anchor="middle" font-size="9" fill="#999">'
        f'Celková plocha: {total_area:.0f} m²</text>'
    )

    lines.append('</svg>')
    return "\n".join(lines)


# ── Vstupní bod ────────────────────────────────────────────────────────────────

def generate_floorplan_svg(intent_model: dict) -> dict:
    """
    Hlavní vstupní bod.
    Vrací: {"svg": str, "room_count": int, "total_area": float}
    """
    nodes, edges = build_spatial_graph(intent_model)
    layout = compute_layout(nodes, edges)
    svg = generate_svg(layout, edges)
    return {
        "svg": svg,
        "room_count": len(layout.rooms),
        "total_area": sum(r.area_target for r in layout.rooms),
    }
