from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "assets" / "nmos-greeter-tweet.png"

WIDTH = 1600
HEIGHT = 900


def clamp_channel(value: float) -> int:
    return max(0, min(255, int(round(value))))


def rgba(color: tuple[int, int, int], alpha: int = 255) -> tuple[int, int, int, int]:
    return color[0], color[1], color[2], alpha


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix_color(start: tuple[int, int, int], end: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        clamp_channel(lerp(start[0], end[0], t)),
        clamp_channel(lerp(start[1], end[1], t)),
        clamp_channel(lerp(start[2], end[2], t)),
    )


def font_paths() -> dict[str, list[str]]:
    return {
        "regular": [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ],
        "semibold": [
            "C:/Windows/Fonts/seguisb.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ],
        "bold": [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ],
        "mono": [
            "C:/Windows/Fonts/consola.ttf",
            "C:/Windows/Fonts/cour.ttf",
        ],
    }


def load_font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in font_paths().get(weight, []):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    anchor: str = "la",
) -> None:
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)


def text_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def add_glow(
    base: Image.Image,
    *,
    center: tuple[int, int],
    size: tuple[int, int],
    color: tuple[int, int, int],
    alpha: int,
    blur_radius: int,
) -> None:
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x, y = center
    w, h = size
    box = (x - w // 2, y - h // 2, x + w // 2, y + h // 2)
    draw.ellipse(box, fill=rgba(color, alpha))
    overlay = overlay.filter(ImageFilter.GaussianBlur(blur_radius))
    base.alpha_composite(overlay)


def add_shadow(
    base: Image.Image,
    box: tuple[int, int, int, int],
    *,
    radius: int,
    offset: tuple[int, int],
    alpha: int,
) -> None:
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    shifted = (
        box[0] + offset[0],
        box[1] + offset[1],
        box[2] + offset[0],
        box[3] + offset[1],
    )
    draw.rounded_rectangle(shifted, radius=radius, fill=(0, 0, 0, alpha))
    overlay = overlay.filter(ImageFilter.GaussianBlur(28))
    base.alpha_composite(overlay)


def draw_checkbox(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    *,
    label_lines: list[str],
    label_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    x, y = xy
    box = (x, y, x + 22, y + 22)
    draw.rounded_rectangle(box, radius=6, fill=(37, 118, 93, 255), outline=(67, 163, 126, 255), width=1)
    draw.line((x + 6, y + 11, x + 10, y + 15), fill=(239, 248, 244, 255), width=3)
    draw.line((x + 10, y + 15, x + 17, y + 7), fill=(239, 248, 244, 255), width=3)
    for index, line in enumerate(label_lines):
        draw_text(draw, (x + 36, y + 2 + (index * 24)), line, font=label_font, fill=(214, 225, 231, 255))


def draw_button(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    label: str,
    label_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
    text_fill: tuple[int, int, int, int],
) -> None:
    draw.rounded_rectangle(box, radius=14, fill=fill, outline=outline, width=1)
    cx = (box[0] + box[2]) // 2
    cy = (box[1] + box[3]) // 2
    draw_text(draw, (cx, cy - 1), label, font=label_font, fill=text_fill, anchor="mm")


def draw_progress(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    progress: float,
) -> None:
    draw.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, fill=(19, 33, 45, 255), outline=(35, 57, 72, 255), width=1)
    fill_width = int((box[2] - box[0]) * max(0.0, min(1.0, progress)))
    fill_box = (box[0], box[1], box[0] + fill_width, box[3])
    draw.rounded_rectangle(fill_box, radius=(box[3] - box[1]) // 2, fill=(38, 153, 127, 255))
    highlight_box = (box[0], box[1], box[0] + fill_width, box[1] + (box[3] - box[1]) // 2)
    draw.rounded_rectangle(highlight_box, radius=(box[3] - box[1]) // 2, fill=(92, 202, 173, 80))


def build_background() -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    pixels = image.load()
    top = (5, 12, 19)
    bottom = (13, 31, 42)
    for y in range(HEIGHT):
        t = y / max(1, HEIGHT - 1)
        line_color = mix_color(top, bottom, t)
        for x in range(WIDTH):
            pixels[x, y] = rgba(line_color)

    add_glow(image, center=(250, 110), size=(620, 420), color=(0, 139, 145), alpha=135, blur_radius=95)
    add_glow(image, center=(1270, 170), size=(540, 360), color=(35, 104, 176), alpha=120, blur_radius=100)
    add_glow(image, center=(1260, 760), size=(760, 360), color=(17, 82, 92), alpha=110, blur_radius=120)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    draw.polygon([(0, 900), (0, 640), (400, 900)], fill=(8, 18, 26, 85))
    draw.polygon([(1150, 0), (1600, 0), (1600, 320)], fill=(14, 25, 33, 95))
    draw.rectangle((0, 0, WIDTH, 44), fill=(6, 13, 19, 175))
    draw.line((0, 44, WIDTH, 44), fill=(36, 55, 68, 150), width=1)

    dock_box = (540, 815, 1060, 875)
    draw.rounded_rectangle(dock_box, radius=28, fill=(7, 14, 20, 180), outline=(45, 67, 81, 150), width=1)

    icon_x = 588
    icon_colors = [
        (39, 140, 117),
        (58, 118, 199),
        (82, 92, 210),
        (216, 136, 39),
        (62, 154, 85),
        (111, 123, 143),
    ]
    for color in icon_colors:
        draw.rounded_rectangle((icon_x, 830, icon_x + 36, 866), radius=10, fill=rgba(color, 255))
        draw.rounded_rectangle((icon_x + 8, 838, icon_x + 28, 858), radius=5, fill=(244, 249, 251, 170))
        icon_x += 66

    image.alpha_composite(overlay)
    return image


def render() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    image = build_background()
    draw = ImageDraw.Draw(image)

    font_regular_18 = load_font(18)
    font_regular_22 = load_font(22)
    font_regular_24 = load_font(24)
    font_regular_26 = load_font(26)
    font_regular_28 = load_font(28)
    font_semibold_18 = load_font(18, "semibold")
    font_semibold_22 = load_font(22, "semibold")
    font_semibold_24 = load_font(24, "semibold")
    font_semibold_28 = load_font(28, "semibold")
    font_semibold_34 = load_font(34, "semibold")
    font_bold_52 = load_font(52, "bold")
    font_bold_18 = load_font(18, "bold")
    font_mono_18 = load_font(18, "mono")

    draw_text(draw, (30, 22), "10:42", font=font_semibold_18, fill=(220, 230, 236, 230), anchor="lm")
    draw_text(draw, (WIDTH // 2, 22), "NM-OS Live Session", font=font_semibold_18, fill=(220, 230, 236, 220), anchor="mm")
    draw_text(draw, (WIDTH - 40, 22), "Tor bootstrap 87%", font=font_semibold_18, fill=(145, 224, 191, 230), anchor="rm")

    window_box = (220, 110, 1380, 760)
    add_shadow(image, window_box, radius=34, offset=(0, 18), alpha=130)
    draw.rounded_rectangle(window_box, radius=34, fill=(11, 18, 26, 244), outline=(39, 57, 72, 255), width=1)

    header_box = (220, 110, 1380, 172)
    draw.rounded_rectangle(header_box, radius=34, fill=(15, 24, 34, 248))
    draw.rectangle((220, 141, 1380, 172), fill=(15, 24, 34, 248))
    draw.line((246, 171, 1354, 171), fill=(36, 53, 67, 255), width=1)

    logo_center = (280, 141)
    draw.ellipse((logo_center[0] - 18, logo_center[1] - 18, logo_center[0] + 18, logo_center[1] + 18), fill=(18, 55, 67, 255))
    draw.ellipse((logo_center[0] - 10, logo_center[1] - 10, logo_center[0] + 10, logo_center[1] + 10), fill=(57, 190, 174, 255))
    draw.ellipse((logo_center[0] - 4, logo_center[1] - 4, logo_center[0] + 4, logo_center[1] + 4), fill=(9, 18, 26, 255))
    draw_text(draw, (314, 141), "NM-OS Greeter", font=font_semibold_24, fill=(236, 242, 245, 255), anchor="lm")
    draw_text(draw, (1336, 141), "Alpha", font=font_semibold_18, fill=(130, 214, 182, 255), anchor="rm")

    content_left = 280
    draw_text(draw, (content_left, 230), "NM-OS", font=font_bold_52, fill=(244, 248, 250, 255))
    draw_text(
        draw,
        (content_left, 292),
        "Prepare your session before entering the desktop.",
        font=font_regular_24,
        fill=(173, 190, 200, 255),
    )

    mode_badge = (content_left, 330, 980, 382)
    draw.rounded_rectangle(mode_badge, radius=18, fill=(18, 33, 46, 255), outline=(42, 70, 88, 255), width=1)
    draw_text(
        draw,
        (content_left + 24, 357),
        "Mode: Strict - Tor-first strict profile is active.",
        font=font_semibold_22,
        fill=(154, 223, 196, 255),
        anchor="lm",
    )

    status_box = (content_left, 402, 704, 446)
    draw.rounded_rectangle(status_box, radius=16, fill=(15, 27, 36, 255), outline=(34, 54, 65, 255), width=1)
    draw_text(draw, (content_left + 20, 424), "Waiting for Tor to become ready.", font=font_regular_22, fill=(219, 228, 233, 255), anchor="lm")

    page_box = (280, 480, 980, 700)
    draw.rounded_rectangle(page_box, radius=28, fill=(14, 22, 31, 255), outline=(33, 50, 64, 255), width=1)
    draw_text(draw, (320, 530), "Network", font=font_semibold_34, fill=(241, 246, 248, 255))

    strict_chip = (834, 508, 938, 548)
    draw.rounded_rectangle(strict_chip, radius=18, fill=(25, 47, 40, 255), outline=(57, 116, 95, 255), width=1)
    draw_text(draw, ((strict_chip[0] + strict_chip[2]) // 2, 528), "STRICT", font=font_bold_18, fill=(160, 228, 198, 255), anchor="mm")

    draw_text(draw, (320, 578), "Waiting for Tor bootstrap", font=font_semibold_28, fill=(214, 225, 231, 255))
    draw_text(draw, (320, 615), "Outbound traffic stays blocked until readiness.", font=font_regular_22, fill=(144, 161, 172, 255))

    draw_progress(draw, (320, 642, 900, 666), progress=0.87)
    draw_text(draw, (924, 654), "87%", font=font_semibold_22, fill=(154, 223, 196, 255), anchor="lm")

    draw_checkbox(
        draw,
        (320, 682),
        label_lines=[
            "Continue to desktop while",
            "network stays blocked",
        ],
        label_font=font_regular_18,
    )

    draw_button(
        draw,
        (734, 676, 940, 720),
        label="Refresh network status",
        label_font=font_semibold_18,
        fill=(18, 31, 43, 255),
        outline=(43, 67, 82, 255),
        text_fill=(221, 229, 234, 255),
    )

    nav_y = 730
    draw_button(
        draw,
        (280, nav_y, 392, nav_y + 44),
        label="Back",
        label_font=font_semibold_18,
        fill=(18, 28, 37, 255),
        outline=(40, 59, 72, 255),
        text_fill=(189, 201, 209, 255),
    )
    draw_button(
        draw,
        (406, nav_y, 526, nav_y + 44),
        label="Next",
        label_font=font_semibold_18,
        fill=(26, 43, 56, 255),
        outline=(53, 76, 90, 255),
        text_fill=(234, 240, 243, 255),
    )
    draw_button(
        draw,
        (540, nav_y, 670, nav_y + 44),
        label="Finish",
        label_font=font_semibold_18,
        fill=(33, 134, 109, 255),
        outline=(71, 172, 145, 255),
        text_fill=(245, 249, 250, 255),
    )

    info_box = (1028, 230, 1320, 410)
    draw.rounded_rectangle(info_box, radius=26, fill=(14, 22, 30, 214), outline=(34, 51, 64, 220), width=1)
    draw_text(draw, (1060, 270), "Current Alpha", font=font_semibold_24, fill=(240, 245, 247, 255))
    info_items = [
        "USB live boot",
        "Tor-first gate",
        "Encrypted persistence",
        "Pre-login setup flow",
    ]
    bullet_y = 306
    for item in info_items:
        draw.ellipse((1060, bullet_y + 5, 1070, bullet_y + 15), fill=(68, 191, 170, 255))
        draw_text(draw, (1086, bullet_y), item, font=font_regular_22, fill=(203, 214, 220, 255))
        bullet_y += 34

    callout_box = (1028, 438, 1320, 680)
    draw.rounded_rectangle(callout_box, radius=26, fill=(16, 26, 35, 220), outline=(37, 55, 68, 220), width=1)
    draw_text(draw, (1060, 482), "Boot Profiles", font=font_semibold_24, fill=(240, 245, 247, 255))

    chip_labels = [
        ("Strict", (33, 134, 109), (245, 249, 250)),
        ("Flexible", (28, 52, 67), (209, 220, 226)),
        ("Offline", (28, 52, 67), (209, 220, 226)),
        ("Recovery", (28, 52, 67), (209, 220, 226)),
    ]

    chip_x = 1060
    chip_y = 534
    for label, chip_color, text_fill in chip_labels:
        width, _ = text_size(draw, label, font=font_semibold_18)
        chip_w = width + 34
        chip_h = 38
        draw.rounded_rectangle((chip_x, chip_y, chip_x + chip_w, chip_y + chip_h), radius=18, fill=rgba(chip_color, 255))
        draw_text(draw, (chip_x + chip_w // 2, chip_y + chip_h // 2 - 1), label, font=font_semibold_18, fill=rgba(text_fill, 255), anchor="mm")
        chip_x += chip_w + 12
        if chip_x > 1240:
            chip_x = 1060
            chip_y += 52

    draw_text(draw, (1060, 628), "Designed to feel practical,", font=font_regular_22, fill=(176, 192, 201, 255))
    draw_text(draw, (1060, 656), "not punishing.", font=font_regular_22, fill=(176, 192, 201, 255))

    footer = "github.com/Krypera/NM-OS"
    footer_box = (280, 790, 520, 832)
    draw.rounded_rectangle(footer_box, radius=18, fill=(9, 16, 22, 160), outline=(38, 58, 70, 160), width=1)
    draw_text(draw, (300, 812), footer, font=font_mono_18, fill=(159, 176, 185, 255), anchor="lm")

    image = image.convert("RGB")
    image.save(OUTPUT, format="PNG", optimize=True)
    return OUTPUT


if __name__ == "__main__":
    path = render()
    print(path)
