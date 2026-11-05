#!/usr/bin/env python3
"""Convierte una foto (persona usando el producto) en un video corto con Higgsfield.

Uso: python3 reels/higgsfield_reel.py reels/pedidos/<archivo>.json

El pedido es un JSON con:
  imagen  -> ruta de la foto dentro del repo (ej. fotos_ia/xxx_persona.jpg)
  prompt  -> qué debe pasar en el video (en inglés funciona mejor)
  salida  -> nombre del video sin extensión (ej. 2026-11-10_reel)
  duracion (opcional) -> 5 o 10 segundos (por defecto 5)

La clave se lee de la variable de entorno HIGGSFIELD_KEY ("ID:SECRETO").
Nunca se imprime ni se guarda en el repo.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

API = "https://api.higgsfield.ai"
MODELO = "/kling-video/v2.5-turbo/standard/image-to-video"
REPO_RAW = "https://raw.githubusercontent.com/ddonoso1992-eng/Kimo-historias/main/"
NEGATIVO = "blurry, distorted hands, extra fingers, deformed product, text, watermark, logo"


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


def main():
    pedido = json.load(open(sys.argv[1], encoding="utf-8"))
    imagen_url = REPO_RAW + pedido["imagen"]
    cuerpo = {
        "prompt": pedido["prompt"],
        "image_url": imagen_url,
        "duration": int(pedido.get("duracion", 5)),
        "negative_prompt": NEGATIVO,
    }
    print(f"Enviando a Higgsfield: {pedido['imagen']} ({cuerpo['duration']} s)")
    resp = llamar("POST", API + MODELO, cuerpo)
    rid = resp["request_id"]
    print(f"request_id: {rid}")

    espera = 10
    for _ in range(60):  # hasta ~15 min
        time.sleep(espera)
        estado = llamar("GET", f"{API}/requests/{rid}/status")
        st = estado.get("status")
        print(f"estado: {st}")
        if st == "completed":
            video = estado["video"]["url"]
            destino = f"reels/{pedido['salida']}.mp4"
            urllib.request.urlretrieve(video, destino)
            print(f"Video guardado en {destino}")
            return
        if st in ("failed", "nsfw", "canceled"):
            sys.exit(f"Higgsfield terminó en estado {st}: {json.dumps(estado)[:500]}")
        espera = min(espera + 5, 20)
    sys.exit("Higgsfield tardó demasiado (más de ~15 min).")


if __name__ == "__main__":
    main()
