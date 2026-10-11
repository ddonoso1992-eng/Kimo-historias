"""KIMO - generador de historias 1080x1920 (marca KIMO 2025).
Uso:
  python3 kimo_historias.py producto  FOTO.png "Titulo" "$18" "Texto corto" salida.jpg
  python3 kimo_historias.py cta       FOTO.png "Titulo" "$18" "Texto corto" salida.jpg
Salida: JPEG liviano (~70-120 KB) listo para subir a Drive en base64.
"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
ROSA, AMAR, MENTA, LILA = "#f8c1cb", "#f8e399", "#8ad5c6", "#c7b8e2"
CELESTE, CORAL, TURQ, AMAR2 = "#3eb8d5", "#fca8a7", "#62cccb", "#f9de7d"
GRIS = "#5f6368"
FD = "/usr/share/fonts/truetype/google-fonts/Poppins-"
WHATS = "+593 98 325 1505"


def f(w, s):
    return ImageFont.truetype(f"{FD}{w}.ttf", s)


def centrado(d, y, txt, font, fill, maxw=940):
    # parte el texto en líneas que quepan
    palabras, lineas, l = txt.split(), [], ""
    for p in palabras:
        t = (l + " " + p).strip()
        if d.textlength(t, font=font) <= maxw:
            l = t
        else:
            lineas.append(l); l = p
    if l:
        lineas.append(l)
    for ln in lineas:
        w = d.textlength(ln, font=font)
        d.text(((W - w) / 2, y), ln, font=font, fill=fill)
        y += int(font.size * 1.18)
    return y


def logo(d, y, size=96):
    fnt = f("Bold", size)
    letras = [("K", ROSA), ("I", AMAR2), ("M", MENTA), ("O", LILA)]
    total = sum(d.textlength(c, font=fnt) for c, _ in letras) + 14 * 3
    x = (W - total) / 2
    for c, col in letras:
        d.text((x, y), c, font=fnt, fill=col)
        x += d.textlength(c, font=fnt) + 14


def fondo():
    im = Image.new("RGB", (W, H), "#fffaf3")
    d = ImageDraw.Draw(im)
    # puntos y estrellas suaves de la marca
    for (x, y, r, c) in [(110, 140, 26, TURQ), (970, 150, 20, CORAL), (60, 1840, 18, LILA),
                         (1020, 1830, 24, AMAR2), (1040, 900, 12, MENTA), (40, 1000, 12, ROSA)]:
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)
    d.rectangle((0, 0, W, 22), fill=AMAR2)
    d.rectangle((0, H - 22, W, H), fill=ROSA)
    return im, d


def foto(path, box_w, box_h):
    p = Image.open(path).convert("RGBA")
    # recorta márgenes blancos/transparentes de la foto de Shopify
    from PIL import ImageChops
    rgb = Image.new("RGB", p.size, "white"); rgb.paste(p, mask=p.split()[3])
    bb = ImageChops.difference(rgb, Image.new("RGB", p.size, "white")).convert("L").point(lambda v: 255 if v > 18 else 0).getbbox()
    if bb:
        m = 30
        p = p.crop((max(bb[0]-m,0), max(bb[1]-m,0), min(bb[2]+m,p.size[0]), min(bb[3]+m,p.size[1])))
    p.thumbnail((box_w, box_h), Image.LANCZOS)
    if p.size[0] < box_w*0.8 and p.size[1] < box_h*0.8:
        r = min(box_w/p.size[0], box_h/p.size[1]); p = p.resize((int(p.size[0]*r), int(p.size[1]*r)), Image.LANCZOS)
    return p


def tarjeta(im, prod, cx, cy, pad=40, color="white"):
    w, h = prod.size
    sh = Image.new("RGBA", (w + pad * 2 + 40, h + pad * 2 + 40), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((20, 30, w + pad * 2 + 20, h + pad * 2 + 30), 60, fill=(0, 0, 0, 40))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    x0, y0 = int(cx - (w + pad * 2) / 2), int(cy - (h + pad * 2) / 2)
    im.paste(sh, (x0 - 20, y0 - 20), sh)
    ImageDraw.Draw(im).rounded_rectangle((x0, y0, x0 + w + pad * 2, y0 + h + pad * 2), 60, fill=color)
    im.paste(prod, (x0 + pad, y0 + pad), prod)
    return y0 + h + pad * 2


def precio(d, y, txt):
    fnt = f("Bold", 92)
    w = d.textlength(txt, font=fnt) + 120
    x = (W - w) / 2
    d.rounded_rectangle((x, y, x + w, y + 150), 75, fill=CELESTE)
    d.text((x + 60, y + 18), txt, font=fnt, fill="white")
    return y + 150


def hist_producto(fotop, titulo, pr, texto, out):
    im, d = fondo()
    logo(d, 90)
    y = centrado(d, 250, texto, f("Bold", 74), GRIS)
    prod = foto(fotop, 860, 860)
    fin = tarjeta(im, prod, W / 2, y + 60 + (prod.size[1] + 80) / 2)
    d = ImageDraw.Draw(im)
    yy = centrado(d, fin + 50, titulo, f("Medium", 54), GRIS)
    precio(d, yy + 30, pr)
    centrado(d, H - 150, "Envíos a todo Ecuador", f("Medium", 40), CELESTE)
    guardar(im, out)


def hist_cta(fotop, titulo, pr, texto, out):
    im, d = fondo()
    logo(d, 90)
    prod = foto(fotop, 640, 640)
    fin = tarjeta(im, prod, W / 2, 300 + (prod.size[1] + 80) / 2, color="#fff3f4")
    d = ImageDraw.Draw(im)
    yy = centrado(d, fin + 40, f"{titulo} · {pr}", f("Medium", 50), GRIS)
    yy = centrado(d, yy + 40, texto, f("Bold", 80), GRIS)
    # botón WhatsApp
    bw, by = 860, yy + 50
    bx = (W - bw) / 2
    d.rounded_rectangle((bx, by, bx + bw, by + 170), 85, fill="#25D366")
    centrado(d, by + 22, "Escríbenos por WhatsApp", f("Bold", 56), "white")
    centrado(d, by + 98, WHATS, f("Medium", 40), "white")
    centrado(d, H - 150, "Regala sonrisas, regala KIMO", f("Medium", 40), CELESTE)
    guardar(im, out)


def guardar(im, out):
    im.convert("RGB").save(out, "JPEG", quality=66, optimize=True, progressive=True, subsampling=2)


if __name__ == "__main__":
    tipo, fotop, titulo, pr, texto, out = sys.argv[1:7]
    (hist_producto if tipo == "producto" else hist_cta)(fotop, titulo, pr, texto, out)
    import os
    print(out, os.path.getsize(out), "bytes")
