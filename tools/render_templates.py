"""
Renderer isometrico dei template (richiede Pillow: pip install -r requirements-dev.txt).

Uso:
    python tools/render_templates.py                 # PNG di ogni template generato in docs/renders/
    python tools/render_templates.py lighthouse      # solo alcuni
    python tools/render_templates.py --gallery       # anche i fogli riassuntivi docs/gallery_*.png
    python tools/render_templates.py --back          # vista dal lato opposto (ruotata di 180 gradi)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw, ImageFont

import blockinfo as bi
from structure_manager import Structure

TEMPLATES_DIR = os.path.join(HERE, "..", "templates")
OUT_DIR = os.path.join(HERE, "..", "docs", "renders")
GALLERY_DIR = os.path.join(HERE, "..", "docs")

DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
CCW = {"north": "west", "west": "south", "south": "east", "east": "north"}
CW = {v: k for k, v in CCW.items()}


def _stair_boxes(props):
    facing = props.get("facing", "north")
    top = props.get("half") == "top"
    shape = props.get("shape", "straight")
    left, right, back = CCW[facing], CW[facing], facing
    front = {"north": "south", "south": "north", "east": "west", "west": "east"}[facing]
    quads = {"straight": [(back, left), (back, right)],
             "outer_left": [(back, left)], "outer_right": [(back, right)],
             "inner_left": [(back, left), (back, right), (front, left)],
             "inner_right": [(back, left), (back, right), (front, right)]}[shape]
    names = []
    for a, b in quads:
        names.append({a, b})
    base = (0, 0.5, 0, 1, 1, 1) if top else (0, 0, 0, 1, 0.5, 1)
    y0, y1 = (0.0, 0.5) if top else (0.5, 1.0)
    boxes = [base]
    for q in names:
        xs = (0.0, 0.5) if "west" in q else (0.5, 1.0)
        zs = (0.0, 0.5) if "north" in q else (0.5, 1.0)
        boxes.append((xs[0], y0, zs[0], xs[1], y1, zs[1]))
    return boxes


def shape_boxes(n, props, neighbors):
    """List of boxes (x0, y0, z0, x1, y1, z1) in cell units for a block."""
    full = [(0, 0, 0, 1, 1, 1)]
    if n.endswith("_stairs"):
        return _stair_boxes(props)
    if n.endswith("_slab"):
        t = props.get("type", "bottom")
        return full if t == "double" else [(0, 0.5, 0, 1, 1, 1)] if t == "top" else [(0, 0, 0, 1, 0.5, 1)]
    if n.endswith("_fence") or n.endswith("pane") or n == "iron_bars" or bi.is_wall_block(n):
        wall = bi.is_wall_block(n)
        a, b = (0.25, 0.75) if wall else (0.375, 0.625) if n.endswith("_fence") else (0.44, 0.56)
        h = 1.0 if not wall else 0.875
        arm_h = (0.0, 0.8125) if wall else (0.35, 0.95) if n.endswith("_fence") else (0.0, 1.0)
        boxes = [(a, 0, a, b, h if not wall or props.get("up", "true") == "true" else 0.8125, b)]
        arm_a, arm_b = (0.3125, 0.6875) if wall else (0.44, 0.56)
        for d, (dx, dz) in DIRS.items():
            if props.get(d, "false") not in ("false", "none"):
                if dx:
                    boxes.append((0 if dx < 0 else b, arm_h[0], arm_a, a if dx < 0 else 1, arm_h[1], arm_b))
                else:
                    boxes.append((arm_a, arm_h[0], 0 if dz < 0 else b, arm_b, arm_h[1], a if dz < 0 else 1))
        return boxes
    if n.endswith("_carpet") or n.endswith("pressure_plate") or n in ("rail", "lily_pad", "moss_carpet"):
        return [(0, 0, 0, 1, 0.07, 1)]
    if n == "snow":
        return [(0, 0, 0, 1, 0.125 * int(props.get("layers", "1")), 1)]
    if n.endswith("_door"):
        dx, dz = DIRS[props.get("facing", "north")]
        if dx:
            return [(0, 0, 0, 0.19, 1, 1)] if dx > 0 else [(0.81, 0, 0, 1, 1, 1)]
        return [(0, 0, 0, 1, 1, 0.19)] if dz > 0 else [(0, 0, 0.81, 1, 1, 1)]
    if n.endswith("_trapdoor"):
        return [(0, 0.81, 0, 1, 1, 1)] if props.get("half") == "top" else [(0, 0, 0, 1, 0.19, 1)]
    if n in ("ladder",):
        dx, dz = DIRS[props.get("facing", "north")]
        if dx:
            return [(0, 0, 0, 0.12, 1, 1)] if dx > 0 else [(0.88, 0, 0, 1, 1, 1)]
        return [(0, 0, 0, 1, 1, 0.12)] if dz > 0 else [(0, 0, 0.88, 1, 1, 1)]
    if n in ("torch", "soul_torch", "redstone_torch", "end_rod", "lightning_rod"):
        return [(0.44, 0, 0.44, 0.56, 0.65 if "torch" in n else 1, 0.56)]
    if n.endswith("wall_torch"):
        dx, dz = DIRS[props.get("facing", "north")]
        cx, cz = 0.5 - dx * 0.3, 0.5 - dz * 0.3
        return [(cx - 0.06, 0.2, cz - 0.06, cx + 0.06, 0.85, cz + 0.06)]
    if n in ("lantern", "soul_lantern"):
        return [(0.31, 0.06, 0.31, 0.69, 0.5, 0.69)] if props.get("hanging") == "true" else [(0.31, 0, 0.31, 0.69, 0.45, 0.69)]
    if n.endswith("_bed"):
        return [(0, 0, 0, 1, 0.56, 1)]
    if n in ("chest", "trapped_chest", "ender_chest"):
        return [(0.06, 0, 0.06, 0.94, 0.88, 0.94)]
    if n in ("campfire", "soul_campfire"):
        return [(0, 0, 0, 1, 0.44, 1)]
    if n in ("farmland", "dirt_path"):
        return [(0, 0, 0, 1, 0.94, 1)]
    if n in ("enchanting_table",):
        return [(0, 0, 0, 1, 0.75, 1)]
    if n.startswith("potted_") or n == "flower_pot":
        return [(0.31, 0, 0.31, 0.69, 0.4, 0.69)]
    if n.endswith("candle"):
        return [(0.44, 0, 0.44, 0.56, 0.4, 0.56)]
    if n in ("wheat", "carrots", "potatoes", "beetroots"):
        return [(0.1, 0, 0.1, 0.9, 0.2 + 0.1 * min(int(props.get("age", "7")), 7), 0.9)]
    if bi.is_plant(n):
        h = 1.0 if n in ("sugar_cane", "cactus", "bamboo") else 0.6
        w = (0.12, 0.88) if n in ("cactus", "sugar_cane") else (0.25, 0.75)
        return [(w[0], 0, w[0], w[1], h, w[1])]
    if n in ("bell", "grindstone", "anvil", "lectern", "brewing_stand", "stonecutter", "conduit"):
        return [(0.12, 0, 0.12, 0.88, 0.8, 0.88)]
    if n in ("vine", "glow_lichen", "cobweb", "tripwire", "redstone_wire", "lever"):
        return [(0.1, 0, 0.1, 0.9, 0.1, 0.9)]
    return full


class IsoRenderer:
    def __init__(self, scale=8):
        self.s = scale

    def project(self, x, y, z):
        s = self.s
        return ((x - z) * s * 0.866, (x + z) * s * 0.5 - y * s)

    def render(self, struct, title=None, ground=True, max_size=900):
        names = {}
        props = {}
        for p, b in struct.blocks.items():
            n = bi.short(b["Name"])
            if n in bi.AIR_LIKE:
                continue
            names[p] = n
            props[p] = b.get("Properties", {})
        w, h, l = struct.width, struct.height, struct.length
        # Adaptive scale
        span_x = (w + l) * 0.866
        span_y = (w + l) * 0.5 + h
        self.s = max(3, min(16, int(min(max_size / max(span_x, 1), max_size / max(span_y, 1)))))
        pad = 12
        min_x = -l * self.s * 0.866 - pad
        max_x = w * self.s * 0.866 + pad
        min_y = -h * self.s - pad - (24 if title else 0)
        max_y = (w + l) * self.s * 0.5 + pad + self.s
        img = Image.new("RGBA", (int(max_x - min_x), int(max_y - min_y)), (24, 26, 32, 255))
        draw = ImageDraw.Draw(img, "RGBA")
        ox, oy = -min_x, -min_y

        def poly(points, color, outline=True):
            pts = [(px + ox, py + oy) for px, py in points]
            r, g, b, a = color
            draw.polygon(pts, fill=(r, g, b, a))
            if outline and self.s >= 5:
                draw.line(pts + [pts[0]], fill=(max(r - 45, 0), max(g - 45, 0), max(b - 45, 0), min(a + 40, 255)), width=1)

        def shade(color, f):
            r, g, b, a = color
            return (int(r * f), int(g * f), int(b * f), a)

        def draw_box(x, y, z, box, color, faces=(True, True, True)):
            x0, y0, z0, x1, y1, z1 = box
            X0, X1, Y0, Y1, Z0, Z1 = x + x0, x + x1, y + y0, y + y1, z + z0, z + z1
            P = self.project
            top, east, south = faces
            if east:
                poly([P(X1, Y0, Z0), P(X1, Y0, Z1), P(X1, Y1, Z1), P(X1, Y1, Z0)], shade(color, 0.78))
            if south:
                poly([P(X0, Y0, Z1), P(X1, Y0, Z1), P(X1, Y1, Z1), P(X0, Y1, Z1)], shade(color, 0.62))
            if top:
                poly([P(X0, Y1, Z0), P(X1, Y1, Z0), P(X1, Y1, Z1), P(X0, Y1, Z1)], color)

        if ground:
            g = (88, 132, 60, 255)
            for x in range(-1, w + 1):
                for z in range(-1, l + 1):
                    c = g if (x + z) % 2 else (82, 124, 56, 255)
                    draw_box(x, -1, z, (0, 0.9, 0, 1, 1, 1), c, (True, x == w, z == l))

        def opaque(p):
            n = names.get(p)
            return n is not None and bi.is_full_solid(n) and not bi.is_transparent_full(n)

        order = sorted(names, key=lambda p: (p[0] + p[1] + p[2], p[1], p[0]))
        for (x, y, z) in order:
            n = names[(x, y, z)]
            color = bi.block_color(n)
            boxes = shape_boxes(n, props[(x, y, z)], None)
            if boxes == [(0, 0, 0, 1, 1, 1)]:
                faces = (not opaque((x, y + 1, z)), not opaque((x + 1, y, z)), not opaque((x, y, z + 1)))
                if not any(faces):
                    continue
                draw_box(x, y, z, boxes[0], color, faces)
            else:
                for box in sorted(boxes, key=lambda bx: (bx[0] + bx[3] + bx[2] + bx[5], bx[1])):
                    draw_box(x, y, z, box, color)
        if title:
            try:
                font = ImageFont.truetype("arial.ttf", 16)
            except OSError:
                font = ImageFont.load_default()
            draw.text((10, 6), title, fill=(235, 235, 240, 255), font=font)
        return img.convert("RGB")


def gallery(images, path, cols=4, cell=420):
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * cell), (18, 19, 24))
    for i, img in enumerate(images):
        im = img.copy()
        im.thumbnail((cell - 8, cell - 8))
        x = (i % cols) * cell + (cell - im.width) // 2
        y = (i // cols) * cell + (cell - im.height) // 2
        sheet.paste(im, (x, y))
    sheet.quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(path, optimize=True)


def main(argv):
    import build_templates
    reg = build_templates.all_templates()
    names = [a for a in argv if not a.startswith("--")] or list(reg)
    back = "--back" in argv
    os.makedirs(OUT_DIR, exist_ok=True)
    renderer = IsoRenderer()
    by_cat = {}
    for name in names:
        path = os.path.join(TEMPLATES_DIR, f"{name}.nbt")
        if not os.path.exists(path):
            print(f"manca {path}")
            continue
        s = Structure.load(path)
        if back:
            s = s.rotate(180)
        title = reg[name]["title"] if name in reg else name
        img = renderer.render(s, title=title)
        out = os.path.join(OUT_DIR, f"{name}{'_back' if back else ''}.png")
        img.quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(out, optimize=True)
        by_cat.setdefault(reg.get(name, {}).get("category", "Altro"), []).append(img)
        print(f"{name:28s} -> {os.path.relpath(out)}")
    if "--gallery" in argv:
        for cat, imgs in by_cat.items():
            p = os.path.join(GALLERY_DIR, f"gallery_{cat.lower().replace(' ', '_')}.png")
            gallery(imgs, p)
            print(f"galleria {cat}: {os.path.relpath(p)}")


if __name__ == "__main__":
    main(sys.argv[1:])
