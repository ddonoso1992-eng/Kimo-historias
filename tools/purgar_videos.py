#!/usr/bin/env python3
"""Purga semanal: saca del repo los videos viejos para no pasar el límite de 50 MB de jsDelivr.

Cada video con más de DIAS días (según la fecha al inicio de su nombre) se copia a la sección
Releases del repo, en la publicación "respaldo-videos". Solo se borra del repo si la copia se
pudo volver a bajar y es idéntica. Nunca toca lo que siga programado o en proceso, ni los videos
sin fecha en el nombre.

--prueba: comprueba el respaldo con un archivo pequeño y lista qué se purgaría, sin borrar videos.
"""
import datetime as dt
import glob
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import shutil

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TAG = "respaldo-videos"
DIAS = 7
LIMITE_MB = 45  # aviso antes de llegar a los 50 MB de jsDelivr
VIDEO = (".mp4", ".mov")
QUITO = dt.timezone(dt.timedelta(hours=-5))


def correr(*args):
    return subprocess.run(args, cwd=RAIZ, check=True, capture_output=True, text=True).stdout.strip()


def git(*args):
    return correr("git", *args)


def gh(*args):
    return correr("gh", *args)


def huella(ruta):
    return hashlib.sha256(pathlib.Path(ruta).read_bytes()).hexdigest()


def en_uso():
    """Archivos que todavía se van a publicar."""
    usados = set()
    for patron in ("programados/*.json", "programados/en_proceso/*.json"):
        for ruta in glob.glob(str(RAIZ / patron)):
            try:
                archivo = json.loads(pathlib.Path(ruta).read_text(encoding="utf-8")).get("archivo")
            except ValueError:
                raise SystemExit(f"No se pudo leer {ruta}: no se purga nada")
            if archivo:
                usados.add(archivo)
    return usados


def candidatos(hoy):
    usados = en_uso()
    lista = []
    for ruta in git("ls-files", "reels", "historias").splitlines():
        if not ruta.lower().endswith(VIDEO):
            continue
        fecha = re.match(r"(\d{4}-\d\d-\d\d)", pathlib.Path(ruta).name)
        if not fecha:
            print(f"Sin fecha, se queda: {ruta}")
            continue
        if ruta in usados:
            print(f"Programado, se queda: {ruta}")
            continue
        if (hoy - dt.date.fromisoformat(fecha.group(1))).days > DIAS:
            lista.append(ruta)
    return lista


def asegurar_release():
    try:
        gh("release", "view", TAG)
    except subprocess.CalledProcessError:
        gh("release", "create", TAG, "--title", "Respaldo de videos", "--latest=false",
           "--notes", "Videos ya usados que la purga semanal sacó del repo.")


def respaldar(ruta, nombre):
    """Sube el archivo y lo vuelve a bajar para confirmar que la copia es idéntica."""
    with tempfile.TemporaryDirectory() as carpeta:
        copia = pathlib.Path(carpeta) / nombre
        shutil.copyfile(ruta, copia)
        gh("release", "upload", TAG, str(copia), "--clobber")
        bajada = pathlib.Path(carpeta) / "bajada"
        gh("release", "download", TAG, "--pattern", nombre, "--output", str(bajada), "--clobber")
        if huella(bajada) != huella(ruta):
            raise ValueError("la copia no coincide con el original")


def peso_mb():
    return sum((RAIZ / r).stat().st_size for r in git("ls-files").splitlines() if (RAIZ / r).is_file()) / 1048576


def guardar(mensaje):
    git("-c", "user.name=KIMO Claude", "-c", "user.email=noreply@anthropic.com", "commit", "-m", mensaje)
    for intento in range(5):
        try:
            git("pull", "--rebase", "origin", "main")
            git("push", "origin", "HEAD:main")
            return
        except subprocess.CalledProcessError:
            if intento == 4:
                raise
            time.sleep(5 * (intento + 1))


def prueba(lista):
    with tempfile.TemporaryDirectory() as carpeta:
        muestra = pathlib.Path(carpeta) / "prueba_respaldo.txt"
        muestra.write_text(f"prueba {dt.datetime.now(QUITO).isoformat()}\n", encoding="utf-8")
        respaldar(muestra, muestra.name)
    gh("release", "delete-asset", TAG, muestra.name, "--yes")
    print("Respaldo OK: el archivo de prueba se subió, se comprobó y se borró")
    print(f"Se purgarían {len(lista)} videos: {lista}")
    print(f"Peso actual del repo: {peso_mb():.1f} MB")
    return 0


def main():
    hoy = dt.datetime.now(QUITO).date()
    lista = candidatos(hoy)
    asegurar_release()
    if "--prueba" in sys.argv:
        return prueba(lista)

    borrados = []
    fallos = 0
    for ruta in lista:
        try:
            respaldar(RAIZ / ruta, ruta.replace("/", "__"))
        except (subprocess.CalledProcessError, ValueError, OSError) as e:
            detalle = getattr(e, "stderr", "") or e
            print(f"ERROR, se queda en el repo: {ruta}: {detalle}")
            fallos += 1
            continue
        git("rm", "-q", "--", ruta)
        borrados.append(ruta)
        print(f"Respaldado y sacado del repo: {ruta}")
    if borrados:
        guardar(f"Purga semanal: {len(borrados)} videos pasados a Releases")

    peso = peso_mb()
    print(f"Purgados: {len(borrados)}. Peso del repo: {peso:.1f} MB")
    if peso > LIMITE_MB:
        print(f"ERROR: el repo pesa más de {LIMITE_MB} MB; jsDelivr puede volver a dar 403")
        fallos += 1
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
