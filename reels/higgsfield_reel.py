#!/usr/bin/env python3
"""Reels de venta para KIMO con Higgsfield.

Uso: python3 reels/higgsfield_reel.py reels/pedidos/<archivo>.json

Pedido (JSON):
  imagen   -> foto dentro del repo (ej. fotos_ia/xxx_persona.jpg). Puede ir por clip.
  clips    -> lista de clips; cada uno {"prompt": "...", "duracion": 5|10, "imagen": opcional}
              (o "prompt" + "duracion" sueltos para un solo clip)
  salida   -> nombre del video final sin extensión (ej. 2026-11-10_reel)
  textos   -> opcional, textos de venta encima del video (sin emojis; usa \n para 2 líneas):
              {"gancho": "...", "precio": "...", "cierre": "...", "whatsapp": "..."}

Cada clip de Higgsfield dura máximo 10 s. Si hay varios, se unen en uno solo,
se pasa a vertical 1080x1920 (formato reel) y se ponen los textos.
La clave se lee de HIGGSFIELD_KEY ("ID:SECRETO"); nunca se imprime.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "https://api.higgsfield.ai"
MODELO = "/kling-video/v2.5-turbo/standard/image-to-video"
REPO_RAW = "https://raw.githubusercontent.com/ddonoso1992-eng/Kimo-historias/main/"
NEGATIVO = ("blurry, distorted hands, extra fingers, deformed jewelry, changing product, "
            "text, watermark, logo, low quality")
FUENTE = os.path.join(os.path.dirname(__file__), "fonts", "Poppins-Bold.ttf")


def llamar(metodo, url, cuerpo=None):
    clave = os.environ.get("HIGGSFIELD_KEY", "").strip()
    if ":" not in clave:
        sys.exit("Falta HIGGSFIELD_KEY (formato ID:SECRETO) en los secretos del repo.")
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(url, data=datos, method=metodo)
    req.add_header("Authorization", f"Key {clave}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"Higgsfield respondió {e.code}: {e.read().decode()[:500]}")


def enviar(imagen, prompt, duracion):
    cuerpo = {"prompt": prompt, "image_url": REPO_RAW + imagen,
              "duration": int(duracion), "negative_prompt": NEGATIVO}
    resp = llamar("POST", API + MODELO, cuerpo)
    print(f"Clip enviado ({duracion} s): {resp['request_id']}")
    return resp["request_id"]


def esperar(rid, destino):
    espera = 10
    for _ in range(80):  # hasta ~20 min
        time.sleep(espera)
        estado = llamar("GET", f"{API}/requests/{rid}/status")
        st = estado.get("status")
        print(f"{rid}: {st}")
        if st == "completed":
            urllib.request.urlretrieve(estado["video"]["url"], destino)
            return
        if st in ("failed", "nsfw", "canceled"):
            sys.exit(f"Higgsfield terminó en estado {st}: {json.dumps(estado)[:500]}")
        espera = min(espera + 5, 20)
    sys.exit("Higgsfield tardó demasiado.")


def ff(args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + args, check=True)


def texto(nombre, contenido):
    ruta = f"/tmp/{nombre}.txt"
    open(ruta, "w", encoding="utf-8").write(contenido)
    return ruta


def armar(clips, salida, textos):
    # 1) cada clip a vertical 1080x1920 con fondo difuminado, mismo fps
    verticales = []
    for i, c in enumerate(clips):
        v = f"/tmp/vert_{i}.mp4"
        ff(["-i", c, "-filter_complex",
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:2[bg];"
            "[0:v]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,fps=30,format=yuv420p[v]",
            "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", v])
        verticales.append(v)
    # 2) unir
    lista = "/tmp/lista.txt"
    open(lista, "w").write("".join(f"file '{v}'\n" for v in verticales))
    unido = "/tmp/unido.mp4"
    ff(["-f", "concat", "-safe", "0", "-i", lista, "-c", "copy", unido])
    dur = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", unido]).decode())
    # 3) textos de venta
    if textos:
        f = FUENTE.replace(":", r"\:")
        caja = "box=1:boxcolor=black@0.45:boxborderw=28"
        filtros = []
        if textos.get("gancho"):
            filtros.append(f"drawtext=fontfile={f}:textfile={texto('g', textos['gancho'])}:fontsize=74:"
                           f"fontcolor=white:{caja}:x=(w-tw)/2:y=h*0.10:enable='between(t,0,3.5)'")
        if textos.get("precio"):
            filtros.append(f"drawtext=fontfile={f}:textfile={texto('p', textos['precio'])}:fontsize=66:line_spacing=14:"
                           f"fontcolor=0xFFE14D:{caja}:x=(w-tw)/2:y=h*0.66:"
                           f"enable='between(t,3,{dur:.2f})'")
        fin = max(dur - 4, 0)
        if textos.get("cierre"):
            filtros.append(f"drawtext=fontfile={f}:textfile={texto('c', textos['cierre'])}:fontsize=64:"
                           f"fontcolor=white:{caja}:x=(w-tw)/2:y=h*0.10:enable='gte(t,{fin:.2f})'")
        if textos.get("whatsapp"):
            filtros.append(f"drawtext=fontfile={f}:textfile={texto('w', textos['whatsapp'])}:fontsize=54:"
                           f"fontcolor=white:box=1:boxcolor=0x25D366@0.9:boxborderw=24:x=(w-tw)/2:y=h*0.88:"
                           f"enable='gte(t,{fin:.2f})'")
        ff(["-i", unido, "-vf", ",".join(filtros), "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", salida])
    else:
        os.replace(unido, salida)
    print(f"Reel listo: {salida} ({dur:.1f} s)")


def main():
    pedido = json.load(open(sys.argv[1], encoding="utf-8"))
    clips = pedido.get("clips") or [{"prompt": pedido["prompt"], "duracion": pedido.get("duracion", 5)}]
    # mandar todos los clips a la vez y luego esperarlos
    ids = [enviar(c.get("imagen", pedido.get("imagen")), c["prompt"], c.get("duracion", 10)) for c in clips]
    archivos = []
    for i, rid in enumerate(ids):
        destino = f"/tmp/clip_{i}.mp4"
        esperar(rid, destino)
        archivos.append(destino)
    armar(archivos, f"reels/{pedido['salida']}.mp4", pedido.get("textos"))


if __name__ == "__main__":
    main()
