#!/usr/bin/env python3
"""Create a transparent master, preview, and ten cropped sticker PNGs."""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


IDS = ["M01", "M02", "M03", "A01", "A02", "A03", "A04", "A05", "A06", "A07"]


def parse_color(value: str) -> np.ndarray:
    value = value.removeprefix("#")
    if len(value) != 6:
        raise ValueError("--background-color must be a six-digit hex color")
    try:
        color = np.array([int(value[index:index + 2], 16) for index in (0, 2, 4)], dtype=np.float32)
    except ValueError as error:
        raise ValueError("--background-color must be a six-digit hex color") from error
    if color.max() - color.min() < 160:
        raise ValueError("--background-color must be highly saturated")
    return color


def make_transparent(image: Image.Image, background_color: str | None) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = np.asarray(rgba.getchannel("A"))
    if alpha.min() < 255:
        return rgba

    if background_color is None:
        raise ValueError("Opaque input requires --background-color; checkerboard inference is intentionally unsupported")

    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    declared_background = parse_color(background_color)
    band = max(4, min(rgb.shape[:2]) // 100)
    border_pixels = np.concatenate([
        rgb[:band].reshape(-1, 3), rgb[-band:].reshape(-1, 3),
        rgb[:, :band].reshape(-1, 3), rgb[:, -band:].reshape(-1, 3),
    ])
    background = np.median(border_pixels, axis=0)
    if float(np.linalg.norm(background - declared_background)) > 35:
        raise ValueError("Image border does not match the declared solid background color")

    distance = np.sqrt(((rgb - background) ** 2).sum(axis=2))
    border_distance = np.sqrt(((border_pixels - background) ** 2).sum(axis=1))
    border_noise = float(np.quantile(border_distance, 0.99))
    if border_noise > 35:
        raise ValueError("Image border is not a sufficiently solid background")

    background_threshold = max(12.0, border_noise + 3.0)
    seed_threshold = max(110.0, background_threshold)
    foreground_threshold = 220.0
    edge_opacity = np.clip(
        (distance - seed_threshold) / (foreground_threshold - seed_threshold),
        0.0,
        1.0,
    )

    # Start from pixels that are truly background-colored, including enclosed
    # holes, then absorb only their antialiased halo. Nearby artwork with no
    # background-colored seed stays opaque instead of being erased globally.
    candidate = distance < foreground_threshold
    core = distance <= seed_threshold
    connected = core
    height, width = candidate.shape
    for _ in range(4):
        connected = np.asarray(
            Image.fromarray(connected).filter(ImageFilter.MaxFilter(3)),
            dtype=bool,
        ) & candidate

    opacity = np.ones(candidate.shape, dtype=np.float32)
    opacity[connected] = edge_opacity[connected]

    colors = rgb.copy()
    known = ~connected
    visible = opacity > 0
    for _ in range(20):
        totals = np.zeros_like(colors)
        counts = np.zeros((height, width), dtype=np.float32)
        for dy, dx in (
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1), (0, 1),
            (1, -1), (1, 0), (1, 1),
        ):
            source_y0, source_y1 = max(0, -dy), min(height, height - dy)
            source_x0, source_x1 = max(0, -dx), min(width, width - dx)
            target_y0, target_y1 = source_y0 + dy, source_y1 + dy
            target_x0, target_x1 = source_x0 + dx, source_x1 + dx
            neighbor_known = known[source_y0:source_y1, source_x0:source_x1]
            totals[target_y0:target_y1, target_x0:target_x1] += (
                colors[source_y0:source_y1, source_x0:source_x1] * neighbor_known[:, :, None]
            )
            counts[target_y0:target_y1, target_x0:target_x1] += neighbor_known
        fill = visible & ~known & (counts > 0)
        if not fill.any():
            break
        colors[fill] = totals[fill] / counts[fill, None]
        known[fill] = True

    unresolved = visible & ~known
    opacity[unresolved] = 0
    opacity[np.rint(opacity * 255) <= 8] = 0
    colors[opacity == 0] = 0
    result = np.dstack([colors, np.rint(opacity * 255)]).astype(np.uint8)
    result[result[:, :, 3] == 0, :3] = 0
    return Image.fromarray(result, "RGBA")


def load_boxes(path: Path, width: int, height: int) -> dict[str, tuple[int, int, int, int]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("boxes.json must be a list")
    found: dict[str, tuple[int, int, int, int]] = {}
    for item in data:
        element_id = item.get("id")
        box = item.get("box")
        if element_id in found or element_id not in IDS:
            raise ValueError(f"Invalid or duplicate element id: {element_id}")
        if not isinstance(box, list) or len(box) != 4 or not all(isinstance(v, int) for v in box):
            raise ValueError(f"Invalid box for {element_id}")
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            raise ValueError(f"Out-of-range box for {element_id}: {box}")
        found[element_id] = (x0, y0, x1, y1)
    if set(found) != set(IDS):
        raise ValueError(f"Expected exactly {IDS}; got {sorted(found)}")
    return found


def crop_element(
    master: Image.Image,
    box: tuple[int, int, int, int],
    element_id: str,
) -> tuple[Image.Image, tuple[int, int]]:
    crop = master.crop(box)
    rgba = np.asarray(crop.convert("RGBA")).copy()
    alpha = rgba[:, :, 3]
    visible = alpha > 0
    solid = alpha > 250
    edge_connected = np.zeros(visible.shape, dtype=bool)
    queue: deque[tuple[int, int]] = deque()
    height, width = visible.shape
    for y in range(height):
        for x in (0, width - 1):
            if visible[y, x] and not edge_connected[y, x]:
                edge_connected[y, x] = True
                queue.append((y, x))
    for x in range(width):
        for y in (0, height - 1):
            if visible[y, x] and not edge_connected[y, x]:
                edge_connected[y, x] = True
                queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        for next_y, next_x in (
            (y - 1, x - 1), (y - 1, x), (y - 1, x + 1),
            (y, x - 1), (y, x + 1),
            (y + 1, x - 1), (y + 1, x), (y + 1, x + 1),
        ):
            if (
                0 <= next_y < height
                and 0 <= next_x < width
                and solid[next_y, next_x]
                and not edge_connected[next_y, next_x]
            ):
                edge_connected[next_y, next_x] = True
                queue.append((next_y, next_x))
    for _ in range(4):
        edge_connected = np.asarray(
            Image.fromarray(edge_connected).filter(ImageFilter.MaxFilter(3)),
            dtype=bool,
        ) & visible
    rgba[edge_connected] = 0

    visible = rgba[:, :, 3] > 0
    seen = np.zeros(visible.shape, dtype=bool)
    for start_y, start_x in np.argwhere(visible):
        if seen[start_y, start_x]:
            continue
        queue = deque([(int(start_y), int(start_x))])
        seen[start_y, start_x] = True
        count = 0
        tiny: list[tuple[int, int]] = []
        while queue:
            y, x = queue.popleft()
            count += 1
            if count <= 2:
                tiny.append((y, x))
            for next_y, next_x in (
                (y - 1, x - 1), (y - 1, x), (y - 1, x + 1),
                (y, x - 1), (y, x + 1),
                (y + 1, x - 1), (y + 1, x), (y + 1, x + 1),
            ):
                if (
                    0 <= next_y < height
                    and 0 <= next_x < width
                    and visible[next_y, next_x]
                    and not seen[next_y, next_x]
                ):
                    seen[next_y, next_x] = True
                    queue.append((next_y, next_x))
        if count <= 2:
            for y, x in tiny:
                rgba[y, x] = 0

    crop = Image.fromarray(rgba, "RGBA")
    alpha = rgba[:, :, 3]
    if alpha.max() == 0:
        raise ValueError(f"{element_id} box contains no visible pixels")
    visible = crop.getchannel("A").getbbox()
    assert visible is not None
    x0, y0, x1, y1 = visible
    padding = 12
    x0, y0 = max(0, x0 - padding), max(0, y0 - padding)
    x1, y1 = min(crop.width, x1 + padding), min(crop.height, y1 + padding)
    return crop.crop((x0, y0, x1, y1)), (box[0] + x0, box[1] + y0)


def validate(image: Image.Image, name: str) -> None:
    rgba = np.asarray(image.convert("RGBA"))
    if rgba[:, :, 3].min() == 255 or rgba[:, :, 3].max() == 0:
        raise ValueError(f"{name} must contain transparent and visible pixels")
    alpha = rgba[:, :, 3]
    if max(alpha[0].max(), alpha[-1].max(), alpha[:, 0].max(), alpha[:, -1].max()) > 0:
        raise ValueError(f"{name} must have a fully transparent outer edge")
    if np.any(rgba[rgba[:, :, 3] == 0, :3]):
        raise ValueError(f"{name} has non-zero RGB in fully transparent pixels")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--boxes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--diagnostics-dir", type=Path, required=True)
    parser.add_argument("--background-color")
    args = parser.parse_args()

    if args.output.exists() and (not args.output.is_dir() or any(args.output.iterdir())):
        parser.error("--output must be a new or empty directory")
    if args.diagnostics_dir.exists() and (
        not args.diagnostics_dir.is_dir() or any(args.diagnostics_dir.iterdir())
    ):
        parser.error("--diagnostics-dir must be a new or empty directory")
    output_path = args.output.resolve()
    diagnostics_path = args.diagnostics_dir.resolve()
    if output_path == diagnostics_path or output_path in diagnostics_path.parents:
        parser.error("--diagnostics-dir must be outside --output")

    source = Image.open(args.source)
    extracted = make_transparent(source, args.background_color)
    boxes = load_boxes(args.boxes, extracted.width, extracted.height)
    prepared: list[tuple[str, Image.Image, tuple[int, int]]] = []
    for element_id in IDS:
        element, position = crop_element(extracted, boxes[element_id], element_id)
        validate(element, f"{element_id}.png")
        prepared.append((element_id, element, position))

    args.output.mkdir(parents=True, exist_ok=True)
    args.diagnostics_dir.mkdir(parents=True, exist_ok=True)
    elements_dir = args.output / "elements"
    elements_dir.mkdir(exist_ok=True)

    master = Image.new("RGBA", extracted.size)
    for element_id, element, position in prepared:
        element.save(elements_dir / f"{element_id}.png")
        master.alpha_composite(element, position)

    master_path = args.output / "transparent-master.png"
    master.save(master_path)
    validate(master, "transparent-master.png")

    preview = Image.new("RGBA", master.size, (249, 246, 238, 255))
    preview.alpha_composite(master)
    preview.convert("RGB").save(args.output / "preview.png")

    check = Image.new("RGBA", (master.width * 2, master.height))
    for index, color in enumerate(((250, 248, 242, 255), (35, 39, 46, 255))):
        background = Image.new("RGBA", master.size, color)
        background.alpha_composite(master)
        check.alpha_composite(background, (master.width * index, 0))
    check.convert("RGB").save(args.diagnostics_dir / "background-check.png")

    print(json.dumps({
        "master": str(master_path),
        "preview": str(args.output / "preview.png"),
        "diagnostics": "created outside delivery",
        "elements": len(IDS),
        "size": [master.width, master.height],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
