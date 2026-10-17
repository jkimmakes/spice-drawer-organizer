"""Drawer fit, printer-aware panel divisions and cell-anchored connectors."""
from collections import Counter
from copy import deepcopy
import json
import math
from .profile import GAP, LOADED_HEIGHT, MAX_MODULE, PITCH

DEFAULTS = {
    "profile": "ball-4oz",
    "drawer": {"width_mm": None, "depth_mm": None, "height_mm": None},
    "printer": {"bed_width_mm": 250.0, "bed_depth_mm": 210.0, "brim_mm": 3.0},
    "layout": {"columns": None, "rows": None, "track": "universal",
               "max_module_columns": 3, "max_module_rows": 3,
               "clearance_mm": 0.5},
}

def merge_config(value):
    if not isinstance(value, dict):
        raise ValueError("The configuration must be a JSON object")
    result = deepcopy(DEFAULTS)
    for group, settings in value.items():
        if group not in result:
            raise ValueError(f"Unknown configuration field: {group}")
        if group == "profile":
            result[group] = settings
            continue
        if not isinstance(settings, dict):
            raise ValueError(f"{group} must be an object")
        for name, setting in settings.items():
            if name not in result[group]:
                raise ValueError(f"Unknown configuration field: {group}.{name}")
            result[group][name] = setting
    return result

def number(value, name, minimum=0, inclusive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if value < minimum or (value == minimum and not inclusive):
        raise ValueError(f"{name} must be {'at least' if inclusive else 'greater than'} {minimum}")
    return value

def integer(value, name):
    number(value, name)
    if int(value) != value:
        raise ValueError(f"{name} must be an integer")
    return int(value)

def partitions(count, maximum):
    """Balanced divisions avoid a one-cell strip when equal splits fit."""
    pieces = math.ceil(count / maximum)
    width, extra = divmod(count, pieces)
    return [width + (i < extra) for i in range(pieces)]

def plan(config):
    config = merge_config(config)
    if config["profile"] != "ball-4oz":
        raise ValueError("Supported profile: ball-4oz (Ball 4 oz Quilted Crystal, SKU 1440080400)")
    drawer, printer, layout = (config[g] for g in ["drawer", "printer", "layout"])
    for name in ["width_mm", "depth_mm"]:
        number(drawer[name], "drawer." + name)
    if drawer["height_mm"] is not None:
        number(drawer["height_mm"], "drawer.height_mm")
        if drawer["height_mm"] < LOADED_HEIGHT:
            raise ValueError(f"Loaded jars need about {LOADED_HEIGHT:.1f} mm of drawer height")
    for name in ["bed_width_mm", "bed_depth_mm"]:
        number(printer[name], "printer." + name)
    number(printer["brim_mm"], "printer.brim_mm", inclusive=True)
    number(layout["clearance_mm"], "layout.clearance_mm", inclusive=True)
    if layout["track"] not in ["universal", "drawer-specific"]:
        raise ValueError("layout.track must be universal or drawer-specific")
    counts, maxima = [], []
    for axis, field, bed in [(0, "columns", "bed_width_mm"), (1, "rows", "bed_depth_mm")]:
        available = drawer[["width_mm", "depth_mm"][axis]] - layout["clearance_mm"]
        capacity = math.floor((available + GAP + 1e-8) / PITCH[axis])
        requested = layout[field]
        count = capacity if requested is None else integer(requested, "layout." + field)
        if count < 1:
            raise ValueError(f"The drawer cannot fit one jar in the {field} direction")
        if count > capacity:
            raise ValueError(f"Requested {count} {field}; the drawer fits at most {capacity} with this clearance")
        maximum = integer(layout["max_module_" + field], "layout.max_module_" + field)
        if maximum > MAX_MODULE:
            raise ValueError("The tested surface supports modules up to 3 columns by 3 rows")
        fits = math.floor((printer[bed] - 2 * printer["brim_mm"] + GAP + 1e-8) / PITCH[axis])
        if fits < 1:
            raise ValueError(f"Printer {bed} cannot fit one cell and its brim without rotating the jar seats")
        counts.append(count)
        maxima.append(min(maximum, fits))
    columns, rows = counts
    if columns * rows > 10000:
        raise ValueError("Maximum planned layout is 10,000 jars")
    panels, grid, parts = [], {}, Counter()
    y = 0
    for height in partitions(rows, maxima[1]):
        x = 0
        for width in partitions(columns, maxima[0]):
            edges = [1, 1, 1, 1] if layout["track"] == "universal" else [
                int(x > 0), int(x + width < columns), int(y > 0), int(y + height < rows)]
            geometry = f"panel_{width}x{height}_F{''.join(map(str, edges))}"
            panel = dict(id=f"P{len(panels) + 1:02d}", column=x, row=y,
                         columns=width, rows=height, edges=edges, part=geometry)
            panels.append(panel)
            parts[geometry] += 1
            for col in range(x, x + width):
                for row in range(y, y + height):
                    grid[col, row] = panel["id"]
            x += width
        y += height
    connectors = []
    for row in range(rows):
        for col in range(columns):
            owner = grid[col, row]
            if col + 1 < columns and grid[col + 1, row] != owner:
                connectors.append(dict(kind="key_x", column=col + 1, row=row))
            if row + 1 < rows and grid[col, row + 1] != owner:
                connectors.append(dict(kind="key_y", column=col, row=row + 1))
    if layout["track"] == "universal":
        for row in range(rows):
            connectors += [dict(kind="plug_left", column=0, row=row),
                           dict(kind="plug_right", column=columns, row=row)]
        for col in range(columns):
            connectors += [dict(kind="plug_front", column=col, row=0),
                           dict(kind="plug_back", column=col, row=rows)]
    connector_counts = dict(Counter(p["kind"] for p in connectors))
    occupied = [columns * PITCH[0] - GAP, rows * PITCH[1] - GAP]
    return dict(format_version=1, config=config, columns=columns, rows=rows, jars=columns * rows,
                pitch_mm=list(PITCH), footprint_mm=[round(x, 3) for x in occupied],
                free_space_mm=[round(drawer[k] - occupied[i], 3)
                               for i, k in enumerate(["width_mm", "depth_mm"])],
                nominal_loaded_height_mm=LOADED_HEIGHT, panels=panels,
                panel_quantities=dict(parts), connectors=connectors, connector_quantities=connector_counts)

def assembly_svg(spec):
    width, depth = spec["footprint_mm"]
    scale = min(760 / width, 1040 / depth)
    sw, sh = width * scale + 40, depth * scale + 90
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {sw:.2f} {sh:.2f}">',
             '<rect width="100%" height="100%" fill="#fcfaf5"/>',
             f'<text x="{sw/2:.2f}" y="24" text-anchor="middle" font-family="sans-serif" font-size="15">BACK / JAR LIDS ↑</text>']
    for i, panel in enumerate(spec["panels"]):
        x = 20 + panel["column"] * PITCH[0] * scale
        y = 40 + (spec["rows"] - panel["row"] - panel["rows"]) * PITCH[1] * scale
        w = (panel["columns"] * PITCH[0] - GAP) * scale
        h = (panel["rows"] * PITCH[1] - GAP) * scale
        color = ["#cae6df", "#c9ddec"][i % 2]
        lines.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="3" fill="{color}" stroke="#315350"/>')
        for row in range(panel["rows"]):
            for col in range(panel["columns"]):
                cx = x + (col + .5) * PITCH[0] * scale
                cy = y + (row + .5) * PITCH[1] * scale
                lines.append(f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="{29*scale:.2f}" ry="{22*scale:.2f}" fill="none" stroke="#7caaa0"/>')
        lines.append(f'<text x="{x+w/2:.2f}" y="{y+h/2:.2f}" text-anchor="middle" font-family="sans-serif" font-size="18" fill="#193d38">{panel["id"]} · {panel["columns"]}×{panel["rows"]}</text>')
    lines += [f'<text x="{sw/2:.2f}" y="{sh-12:.2f}" text-anchor="middle" font-family="sans-serif" font-size="15">FRONT / HANDLE</text>', '</svg>']
    return "\n".join(lines) + "\n"

def print_plan(spec):
    width, depth = spec["footprint_mm"]
    lines = ["# Your spice drawer", "", f"{spec['columns']} columns × {spec['rows']} rows: **{spec['jars']} jars**.",
             f"Tray footprint: **{width:g} × {depth:g} mm** ({width/25.4:.2f} × {depth/25.4:.2f} in).",
             f"Nominal loaded height: **{LOADED_HEIGHT:.1f} mm**. Track: **{spec['config']['layout']['track']}**.", "",
             "![Panel placement](assembly.svg)", "", "## Print quantities", "",
             "| Part | Quantity |", "| --- | ---: |"]
    for kind, count in {**spec["panel_quantities"], **spec["connector_quantities"]}.items():
        lines.append(f"| [{kind}](stls/{kind}.stl) | {count} |")
    lines += ["", "X keys join panels across the drawer; Y keys join rows front to back.",
              "All panel arrows and connector arrows point toward the lids/back. Keep the jar seats in this orientation.",
              "Universal modules use female sockets on every edge. Fill unused outer sockets with the matching plugs; remove plugs to extend the grid.",
              "", "Print flat at 100% scale. Starting settings: 0.30 mm layers, 0.20 mm first layer, two walls, 5% grid infill, four top/three bottom layers, supports off and a 3 mm brim.",
              "Test one module and a joining key before printing the full set. The tested jar profile is Ball 4 oz regular-mouth Quilted Crystal, SKU 1440080400.",
              "", "The planner checks dimensions and printer fit. Run the STL builder and verifier before printing a generated layout.", ""]
    return "\n".join(lines)

def write_plan(spec, output):
    output.mkdir(parents=True, exist_ok=True)
    (output / "layout.json").write_text(json.dumps(spec, indent=2) + "\n")
    (output / "assembly.svg").write_text(assembly_svg(spec))
    (output / "PRINT_PLAN.md").write_text(print_plan(spec))
