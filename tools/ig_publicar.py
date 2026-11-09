#!/usr/bin/env python3
"""Mini Metricool de KIMO: publica en Instagram lo que esté en programados/ cuando llega su hora.

Cada publicación es un archivo programados/<nombre>.json:
{
  "fecha": "2026-11-11T19:00:00-05:00",
  "tipo": "REEL",                        # REEL, STORY o POST
  "archivo": "reels/2026-11-11_reel.mp4", # ruta en el repo o URL https
  "texto": "Caption del reel",            # REEL y POST
  "cancion": "BbY WOW",                   # REEL: obligatoria, salvo "sin_musica": true
  "audio_id": "2385329925545043",         # opcional, en vez de buscar por "cancion"
  "volumen_musica": 25,                   # opcional, 0-100
  "volumen_video": 0                      # opcional, 0-100
}

Nunca publica dos veces: antes de llamar a Instagram mueve el archivo a programados/en_proceso/ y lo
sube a GitHub. Al terminar queda en programados/publicados/ o programados/errores/, sin reintentos.

Para probar sin publicar, sube programados/comprobar.json con {"busquedas": ["nombre de canción"]}:
el resultado queda en programados/estado/ultima_comprobacion.json.
"""
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

IG_ID = "17841467127423464"  # @kimo.ecu
API = "https://graph.facebook.com/v25.0"
REPO = "ddonoso1992-eng/Kimo-historias"
RAIZ = pathlib.Path(__file__).resolve().parent.parent
COLA = RAIZ / "programados"
MAX_ATRASO = dt.timedelta(hours=3)  # si GitHub se atrasa más que esto, no publica a deshora
ESPERA_MAX = 600
INTENTOS = 3
NO_ENCONTRADO = 2207006  # Instagram a veces no "ve" todavía un contenedor recién creado
ESPERA_NO_ENCONTRADO = 90
TIPOS = {"REEL": "REELS", "STORY": "STORIES", "POST": None}
VIDEO = (".mp4", ".mov")


class ErrorMeta(Exception):
    def __init__(self, mensaje, subcode=None):
        super().__init__(mensaje)
        self.subcode = subcode


def llamar(metodo, ruta, datos=None):
    """Llama a la API. El token va en la cabecera para que nunca salga en una URL o un log."""
    token = os.environ["IG_TOKEN"].strip()
    url = f"{API}/{ruta}"
    cuerpo = None
    if metodo == "GET" and datos:
        url += "?" + urllib.parse.urlencode(datos)
    elif datos:
        cuerpo = urllib.parse.urlencode(datos).encode()
    pedido = urllib.request.Request(url, data=cuerpo, method=metodo, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(pedido, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            err = json.load(e).get("error", {})
        except ValueError:
            err = {}
        msg = err.get("error_user_msg") or err.get("message") or f"HTTP {e.code}"
        raise ErrorMeta(f"{msg} (code {err.get('code')}, subcode {err.get('error_subcode')})",
                        subcode=err.get("error_subcode")) from None


def git(*args):
    return subprocess.run(["git", "-C", str(RAIZ), *args], check=True, capture_output=True, text=True).stdout.strip()


def guardar(mensaje):
    """Commit y push, con reintentos porque otras tareas también suben al repo."""
    git("add", "-A", "programados")
    if not git("status", "--porcelain", "programados"):
        return
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


def urls_publicas(archivo, sha):
    """URLs posibles del archivo, en orden de preferencia."""
    if archivo.startswith("https://"):
        return [archivo]
    if not (RAIZ / archivo).is_file():
        raise ErrorMeta(f"No existe en el repo: {archivo}")
    # raw.githubusercontent sirve los mp4 como octet-stream; jsDelivr con el commit los sirve bien.
    urls = [f"https://cdn.jsdelivr.net/gh/{REPO}@{sha}/{archivo}"]
    # jsDelivr puede dar 403 (el repo pasa su límite de 50 MB): las imágenes tienen respaldo en raw.
    if not archivo.lower().endswith(VIDEO):
        urls.append(f"https://raw.githubusercontent.com/{REPO}/{sha}/{archivo}")
    return urls


def revisar_url(url):
    pedido = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(pedido, timeout=60) as r:
        tipo = r.headers.get("content-type", "")
    if not tipo.startswith(("video/", "image/")):
        raise ErrorMeta(f"El archivo se sirve como {tipo}, Instagram no lo aceptaría: {url}")


def elegir_url(urls):
    """Devuelve la primera URL que responde bien, con 3 intentos por URL."""
    problema = None
    for url in urls:
        for intento in range(3):
            try:
                revisar_url(url)
                return url
            except urllib.error.URLError as e:
                problema = f"{url.split('/')[2]}: {e}"
                print(f"No se pudo revisar el archivo ({problema}), intento {intento + 1}")
                if intento < 2:
                    time.sleep(15)
    raise ErrorMeta(f"El archivo no se pudo descargar ({problema})")


def buscar_audio(busqueda, tipo="music"):
    r = llamar("GET", "ig_audio", {"audio_type": tipo, "user_id": IG_ID, "search_query": busqueda})
    return lista_audio(r)


def lista_audio(r):
    """La respuesta viene en "audio" (a veces con "data" adentro), no en "data" como el resto de la API."""
    a = r.get("audio", r.get("data", []))
    return a.get("data", []) if isinstance(a, dict) else a


def id_audio(item):
    return str(item.get("audio_id") or item.get("id") or "")


def corto(item):
    return {k: item.get(k) for k in ("audio_id", "title", "display_artist")}


def elegir_audio(pub):
    if pub.get("audio_id"):
        return str(pub["audio_id"]), None
    cancion = pub["cancion"].strip()
    candidatos = buscar_audio(cancion)
    for item in candidatos:
        if cancion.lower() in str(item.get("title", "")).lower() and id_audio(item):
            return id_audio(item), item.get("title")
    vistos = ", ".join(str(c.get("title")) for c in candidatos[:5]) or "ninguna"
    raise ErrorMeta(f"Instagram no tiene la canción '{cancion}' disponible. Encontró: {vistos}")


def armar_contenedor(pub, url):
    tipo = pub["tipo"]
    es_video = urllib.parse.urlparse(url).path.lower().endswith(VIDEO)
    datos = {}
    extra = {}
    if tipo == "REEL":
        if not es_video:
            raise ErrorMeta("Un reel necesita un video")
        datos.update(media_type="REELS", video_url=url, caption=pub.get("texto", ""), share_to_feed="true")
        if not pub.get("sin_musica"):
            if not (pub.get("cancion") or pub.get("audio_id")):
                raise ErrorMeta("El reel no tiene canción: no se publica mudo")
            audio, titulo = elegir_audio(pub)
            datos["audio_configuration"] = json.dumps({
                "audio_id": audio,
                "audio_volume": int(pub.get("volumen_musica", 25)),
                "video_volume": int(pub.get("volumen_video", 0)),
            })
            extra = {"audio_id": audio, "cancion": titulo}
    elif tipo == "STORY":
        datos["media_type"] = "STORIES"
        datos["video_url" if es_video else "image_url"] = url
    else:
        if es_video:
            raise ErrorMeta("Un POST es de imagen; para video usa REEL")
        datos.update(image_url=url, caption=pub.get("texto", ""))
    return datos, extra


def esperar(contenedor):
    """True si quedó listo; False si Instagram falló al procesarlo (a veces pasa una vez y a la siguiente no)."""
    inicio = time.time()
    while True:
        try:
            estado = llamar("GET", contenedor, {"fields": "status_code,status"})
        except ErrorMeta as e:
            if e.subcode != NO_ENCONTRADO or time.time() - inicio > ESPERA_NO_ENCONTRADO:
                raise
            time.sleep(10)
            continue
        codigo = estado.get("status_code")
        if codigo == "FINISHED":
            return True
        if codigo in ("ERROR", "EXPIRED"):
            print(f"Contenedor falló: {estado.get('status')}")
            return False
        if time.time() - inicio > ESPERA_MAX:
            raise ErrorMeta(f"Instagram tardó más de {ESPERA_MAX // 60} min procesando (estado {codigo})")
        time.sleep(10)


def confirmar_publicacion(contenedor):
    """Un contenedor solo se puede publicar una vez, así que reintentar no duplica."""
    inicio = time.time()
    while True:
        try:
            return llamar("POST", f"{IG_ID}/media_publish", {"creation_id": contenedor})["id"]
        except ErrorMeta as e:
            if e.subcode != NO_ENCONTRADO or time.time() - inicio > ESPERA_NO_ENCONTRADO:
                raise
            time.sleep(15)


def publicar(pub, sha):
    url = elegir_url(urls_publicas(pub["archivo"], sha))
    datos, extra = armar_contenedor(pub, url)
    for intento in range(INTENTOS):
        contenedor = llamar("POST", f"{IG_ID}/media", datos)["id"]
        if esperar(contenedor):
            break
        if intento == INTENTOS - 1:
            raise ErrorMeta(f"Instagram no pudo procesar el archivo tras {INTENTOS} intentos")
        time.sleep(60)
    media = confirmar_publicacion(contenedor)
    enlace = None
    try:
        enlace = llamar("GET", media, {"fields": "permalink"}).get("permalink")
    except ErrorMeta:
        pass  # las historias a veces no devuelven enlace; ya está publicada
    return {"media_id": media, "enlace": enlace, **extra}


def validar(pub):
    if pub.get("tipo") not in TIPOS:
        raise ErrorMeta(f"Tipo inválido: {pub.get('tipo')}")
    if not pub.get("archivo"):
        raise ErrorMeta("Falta 'archivo'")
    fecha = dt.datetime.fromisoformat(pub["fecha"])
    if fecha.tzinfo is None:
        raise ErrorMeta("La fecha debe llevar zona horaria (-05:00)")
    return fecha


def mover(ruta, carpeta, pub, **resultado):
    destino = COLA / carpeta
    destino.mkdir(parents=True, exist_ok=True)
    pub = {**pub, **resultado, "procesado": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    nueva = destino / ruta.name
    nueva.write_text(json.dumps(pub, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ruta.unlink()
    return nueva


def comprobar():
    pedido = COLA / "comprobar.json"
    busquedas = json.loads(pedido.read_text(encoding="utf-8")).get("busquedas", [])
    salida = {"cuando": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}

    def paso(nombre, funcion):
        try:
            salida[nombre] = funcion()
        except (ErrorMeta, KeyError, urllib.error.URLError) as e:
            salida[nombre] = {"ERROR": str(e)}

    paso("cuenta", lambda: llamar("GET", IG_ID, {"fields": "username,media_count"}))
    paso("permisos", lambda: [p["permission"] for p in llamar("GET", "me/permissions").get("data", [])
                              if p.get("status") == "granted"])
    paso("cupo_24h", lambda: llamar("GET", f"{IG_ID}/content_publishing_limit", {"fields": "config,quota_usage"}))
    for b in busquedas:
        paso(f"musica: {b}", lambda b=b: [corto(i) for i in buscar_audio(b)[:5]])
    paso("tendencia", lambda: [corto(i) for i in lista_audio(
        llamar("GET", "ig_audio", {"audio_type": "music", "user_id": IG_ID}))[:5]])
    (COLA / "estado").mkdir(parents=True, exist_ok=True)
    (COLA / "estado" / "ultima_comprobacion.json").write_text(
        json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pedido.unlink()
    guardar("Comprobación de Instagram")


def main():
    if not os.environ.get("IG_TOKEN", "").strip():
        print("Falta el secreto IG_TOKEN")
        return 1 if list(COLA.glob("*.json")) else 0
    if (COLA / "comprobar.json").exists():
        comprobar()

    ahora = dt.datetime.now(dt.timezone.utc)
    sha = git("rev-parse", "HEAD")
    pendientes = []
    fallos = 0
    for ruta in COLA.glob("*.json"):
        pub = json.loads(ruta.read_text(encoding="utf-8"))
        try:
            fecha = validar(pub)
        except (ErrorMeta, ValueError, KeyError) as e:
            mover(ruta, "errores", pub, error=str(e))
            guardar(f"Error en {ruta.name}")
            print(f"ERROR {ruta.name}: {e}")
            fallos += 1
            continue
        if fecha <= ahora:
            pendientes.append((fecha, ruta, pub))

    for fecha, ruta, pub in sorted(pendientes, key=lambda x: (x[0], x[1].name)):
        if ahora - fecha > MAX_ATRASO:
            mover(ruta, "errores", pub, error="Venció: GitHub no lo corrió a tiempo y no se publica a deshora")
            guardar(f"Vencido {ruta.name}")
            print(f"VENCIDO {ruta.name}")
            fallos += 1
            continue
        # Primero se reclama en GitHub: si algo se corta, nunca sale repetido.
        en_proceso = mover(ruta, "en_proceso", pub)
        guardar(f"Publicando {ruta.name}")
        try:
            resultado = publicar(pub, sha)
            mover(en_proceso, "publicados", pub, **resultado)
            guardar(f"Publicado {ruta.name}")
            print(f"PUBLICADO {ruta.name}: {resultado.get('enlace')}")
        except (ErrorMeta, urllib.error.URLError, KeyError, TimeoutError) as e:
            mover(en_proceso, "errores", pub, error=str(e))
            guardar(f"Error en {ruta.name}")
            print(f"ERROR {ruta.name}: {e}")
            fallos += 1
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
