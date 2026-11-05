#!/usr/bin/env python3
"""Reels de venta para KIMO con Higgsfield.

Uso: python3 reels/higgsfield_reel.py reels/pedidos/<archivo>.json

Pedido (JSON):
  imagen   -> foto dentro del repo (ej. fotos_ia/xxx_persona.jpg). Puede ir por clip.
  clips    -> lista de clips; cada uno {"prompt": "...", "duracion": 5|10, "imagen": opcional,
              "request_id": opcional -> reutiliza un clip ya generado sin volver a pagarlo}
              (o "prompt" + "duracion" sueltos para un solo clip)
  salida   -> nombre del video final sin extensión (ej. 2026-11-10_reel)
  textos   -> opcional, textos de venta encima del video (sin emojis; usa \n para 2 líneas):
              {"gancho": "...", "precio": "...", "cierre": "...", "whatsapp": "..."}
  escena   -> opcional: crea primero la foto con OpenAI (gpt-image-1) a partir de la foto real
              del producto: {"foto_producto": "<URL de Shopify>", "prompt": "..."}
              La foto queda en fotos_ia/<salida>.png y se usa como "imagen".
  solo_imagen -> opcional true: solo crea la foto de la escena y termina (para revisar barato)
  voz      -> opcional: {"guion": "...", "voz": "sage"} agrega voz en off de OpenAI.
              Solo se pide cuando Diego lo aprueba (cuesta centavos).
Al terminar se guarda reels/<salida>.json con los request_id de los clips, para rehacer
el video (por ejemplo con voz) SIN volver a pagar Higgsfield.

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
            # una línea por renglón (algunas versiones de ffmpeg muestran el salto de línea como un cuadrito)
            for j, linea in enumerate(textos["precio"].split("\n")):
                filtros.append(f"drawtext=fontfile={f}:textfile={texto(f'p{j}', linea.strip())}:fontsize=66:"
                               f"fontcolor=0xFFE14D:{caja}:x=(w-tw)/2:y=h*0.64+{j}*110:"
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


def git_subir(rutas, mensaje):
    subprocess.run(["git", "add"] + rutas, check=True)
    subprocess.run(["git", "commit", "-m", mensaje], check=False)
    subprocess.run(["git", "pull", "--rebase", "-q", "origin", "main"], check=True)
    subprocess.run(["git", "push", "-q", "origin", "HEAD:main"], check=True)


def crear_escena(escena, salida):
    clave = os.environ.get("OPENAI_API_KEY", "").strip()
    if not clave:
        sys.exit("Falta OPENAI_API_KEY en los secretos del repo.")
    foto = "/tmp/producto.png"
    urllib.request.urlretrieve(escena["foto_producto"], "/tmp/producto_orig")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "/tmp/producto_orig", foto], check=True)
    r = subprocess.run(
        ["curl", "-sS", "https://api.openai.com/v1/images/edits",
         "-H", f"Authorization: Bearer {clave}",
         "-F", "model=gpt-image-1", "-F", f"image[]=@{foto}",
         "-F", "prompt=" + escena["prompt"] + " Keep the product exactly identical to the reference photo "
                           "(same shape, colors and details). Photorealistic, vertical 2:3, no text, no logos.",
         "-F", "size=1024x1536", "-F", "quality=medium", "-F", "n=1"],
        capture_output=True, text=True, check=True)
    datos = json.loads(r.stdout)
    if "data" not in datos:
        sys.exit(f"OpenAI imagen falló: {r.stdout[:500]}")
    import base64
    destino = f"fotos_ia/{salida}.png"
    open(destino, "wb").write(base64.b64decode(datos["data"][0]["b64_json"]))
    git_subir([destino], f"Foto de escena para reel {salida}")
    time.sleep(20)  # que GitHub publique el archivo antes de mandarlo a Higgsfield
    print(f"Escena creada: {destino}")
    return destino


def poner_voz(video, voz, salida):
    clave = os.environ.get("OPENAI_API_KEY", "").strip()
    if not clave:
        sys.exit("Falta OPENAI_API_KEY en los secretos del repo.")
    estilo = ("Habla en español latinoamericano neutro, como una persona joven de Ecuador grabando un reel: "
              "natural, cercana, emocionada pero sin gritar, con pausas cortas y sonrisa en la voz.")
    cuerpo = json.dumps({"model": "gpt-4o-mini-tts", "voice": voz.get("voz", "sage"),
                         "input": voz["guion"], "instructions": estilo, "response_format": "mp3"}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/audio/speech", data=cuerpo, method="POST")
    req.add_header("Authorization", f"Bearer {clave}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as r:
        open("/tmp/voz.mp3", "wb").write(r.read())
    ff(["-i", video, "-i", "/tmp/voz.mp3", "-filter_complex", "[1:a]adelay=600|600,volume=1.4,apad[voz]",
        "-map", "0:v", "-map", "[voz]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", salida])
    print(f"Voz agregada: {salida}")


def main():
    pedido = json.load(open(sys.argv[1], encoding="utf-8"))
    if pedido.get("escena") and not pedido.get("imagen"):
        pedido["imagen"] = crear_escena(pedido["escena"], pedido["salida"])
    if pedido.get("solo_imagen"):
        return
    clips = pedido.get("clips") or [{"prompt": pedido["prompt"], "duracion": pedido.get("duracion", 5)}]
    # mandar todos los clips a la vez y luego esperarlos
    # si un clip ya trae request_id (ya pagado), solo se descarga; no se vuelve a generar
    ids = [c.get("request_id") or enviar(c.get("imagen", pedido.get("imagen")), c["prompt"], c.get("duracion", 10))
           for c in clips]
    archivos = []
    for i, rid in enumerate(ids):
        destino = f"/tmp/clip_{i}.mp4"
        esperar(rid, destino)
        archivos.append(destino)
    final = f"reels/{pedido['salida']}.mp4"
    if pedido.get("voz"):
        armar(archivos, "/tmp/sin_voz.mp4", pedido.get("textos"))
        poner_voz("/tmp/sin_voz.mp4", pedido["voz"], final)
    else:
        armar(archivos, final, pedido.get("textos"))
    # datos para rehacer sin volver a pagar Higgsfield
    info = dict(pedido)
    info["clips"] = [dict(c, request_id=rid, imagen=c.get("imagen", pedido.get("imagen")))
                     for c, rid in zip(clips, ids)]
    info.pop("escena", None)
    json.dump(info, open(f"reels/{pedido['salida']}.json", "w"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
