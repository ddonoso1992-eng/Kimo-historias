"""Plantilla editorial KIMO para historias (1080x1920).

Uso:
  python3 historia_editorial.py FOTO SALIDA "ETIQUETA" "Titular" "Producto · $precio" "CTA"

FOTO: imagen vertical (ideal 1024x1536 de OpenAI, con zona despejada en el tercio inferior).
Requiere: Pillow, fuentes Lora y Poppins, y el logotipo KIMO (LOGOTIPO.png) junto a este script
o en la ruta de la variable de entorno KIMO_LOGO.
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
INK, MUTED = (60, 50, 46), (120, 105, 96)
GF = os.environ.get("KIMO_FONTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts") + "/")
DISCLAIMER = (
    "Imagen referencial. Antes de comprar, solicita una foto real del producto:",
    "el tamaño y las proporciones pueden variar según el ángulo de la fotografía.",
)
LOGO = os.environ.get("KIMO_LOGO", os.path.join(os.path.dirname(os.path.abspath(__file__)), "LOGOTIPO.png"))


def lora(size, italic=False):
    return ImageFont.truetype(GF + ("Lora-Italic-Variable.ttf" if italic else "Lora-Variable.ttf"), size)


def pop(size, weight="Regular"):
    return ImageFont.truetype(GF + f"Poppins-{weight}.ttf", size)


def render(photo, out, label, headline, product, cta):
    im = Image.open(photo).convert("RGBA")
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x0, y0 = (im.width - W) // 2, (im.height - H) // 2
    c = im.crop((x0, y0, x0 + W, y0 + H))

    # velo crema suave en la parte baja para que el texto respire
    veil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(veil)
    for y in range(1150, H):
        t = min(1, (y - 1150) / 260)
        vd.line([(0, y), (W, y)], fill=(248, 242, 235, int(185 * t)))
    c.alpha_composite(veil)
    d = ImageDraw.Draw(c)

    def ctext(y, text, font, fill, spacing=0):
        if spacing:
            ws = [d.textlength(ch, font=font) for ch in text]
            x = (W - (sum(ws) + spacing * (len(text) - 1))) / 2
            for ch, w in zip(text, ws):
                d.text((x, y), ch, font=font, fill=fill)
                x += w + spacing
        else:
            d.text(((W - d.textlength(text, font=font)) / 2, y), text, font=font, fill=fill)

    lg = Image.open(LOGO).convert("RGBA")
    lw = 150
    lg = lg.resize((lw, int(lg.height * lw / lg.width)), Image.LANCZOS)
    c.paste(lg, ((W - lw) // 2, 1235), lg)

    ctext(1318, label.upper(), pop(22, "Medium"), MUTED, spacing=7)
    size = 62
    while d.textlength(headline, font=lora(size, True)) > 960 and size > 44:
        size -= 2
    ctext(1355, headline, lora(size, True), INK)
    ctext(1440, product, pop(27), INK)
    f = pop(26, "Medium")
    tw = d.textlength(cta, font=f)
    ctext(1490, cta, f, INK)
    d.line([((W - tw) / 2, 1528), ((W + tw) / 2, 1528)], fill=INK, width=2)
    # aviso obligatorio: la foto es referencial y la escala puede variar
    ctext(1548, DISCLAIMER[0], pop(19), MUTED)
    ctext(1572, DISCLAIMER[1], pop(19), MUTED)
    c.convert("RGB").save(out, quality=94)


if __name__ == "__main__":
    render(*sys.argv[1:7])
