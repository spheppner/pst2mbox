"""Generate the pst2mbox icon (assets/icon.png and assets/icon.ico) with Pillow."""

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 1024
OUT = Path(__file__).parent


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def build() -> Image.Image:
    s = SIZE
    # Diagonal blue gradient background in a rounded square
    top, bottom = (37, 99, 235), (14, 165, 233)
    grad = Image.new("RGB", (s, s))
    px = grad.load()
    for y in range(s):
        for x in range(s):
            px[x, y] = lerp(top, bottom, (x + y) / (2 * s))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.22), fill=255)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    white, shade = (255, 255, 255, 255), (203, 213, 225, 255)

    # Envelope body
    ex0, ey0, ex1, ey1 = int(s * 0.14), int(s * 0.22), int(s * 0.86), int(s * 0.62)
    d.rounded_rectangle((ex0, ey0, ex1, ey1), radius=int(s * 0.04), fill=white)
    # Envelope flap
    w = int(s * 0.03)
    d.line([(ex0 + w, ey0 + w), ((ex0 + ex1) // 2, int(s * 0.46)), (ex1 - w, ey0 + w)], fill=(37, 99, 235, 255), width=w, joint="curve")

    # Down arrow (conversion) into an "mbox" tray
    cx = s // 2
    aw = int(s * 0.07)
    d.rectangle((cx - aw, int(s * 0.64), cx + aw, int(s * 0.74)), fill=white)
    d.polygon([(cx - int(s * 0.16), int(s * 0.74)), (cx + int(s * 0.16), int(s * 0.74)), (cx, int(s * 0.86))], fill=white)
    # Tray
    d.line([(int(s * 0.22), int(s * 0.80)), (int(s * 0.22), int(s * 0.90)), (int(s * 0.78), int(s * 0.90)), (int(s * 0.78), int(s * 0.80))], fill=shade, width=int(s * 0.04), joint="curve")
    return img


if __name__ == "__main__":
    icon = build()
    icon.resize((512, 512), Image.LANCZOS).save(OUT / "icon.png")
    icon.save(OUT / "icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)])
    print("Wrote icon.png and icon.ico")
