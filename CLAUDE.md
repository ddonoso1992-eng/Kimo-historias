# KIMO – reglas para las tareas automáticas

Estas tareas corren de madrugada para que Diego despierte con las artes LISTAS.
**No te rindas ante un problema técnico:** usa los respaldos de abajo y termina el trabajo.
Avisa de un bloqueo solo si también fallaron los respaldos.

## Herramientas (antes de diseñar)
- Pillow: `python3 -m pip install -q pillow` (usa `python3 -m pip`, no `pip` a secas: instala en otro Python).
- Fuentes: si falta `/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf`, crea la carpeta y descarga
  Bold, Medium, Regular, SemiBold, ExtraBold y Black desde
  `https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-<Peso>.ttf`.

## Fotos de Shopify bloqueadas (cdn.shopify.com da 403 / "CONNECT tunnel failed")
Respaldo probado el 2026-10-13:
1. Por cada foto, en Zapier `execute_zapier_write_action`: selected_api `GoogleDriveCLIAPI`, action `file`,
   tool_name `google_drive_upload_file`, connection_id `020cf089-43f4-8e93-b9eb-68bfcebf94b3`, params
   `{"file": "<URL de cdn.shopify.com>", "folder": "1tAIHx9aXpbkva97R4qTTUcBiKUtILDWq", "new_name": "tmp_foto_<handle>", "new_extension": "png", "convert": "false"}`.
2. Bájala con `mcp__Google_Drive__download_file_content` (fileId = id que devolvió Zapier). El resultado se
   guarda en un archivo JSON: `jq -r .content <archivo> | base64 -d > FOTO.png`. Compara el md5 con el
   `md5Checksum` de Zapier.
3. Al terminar, manda las `tmp_foto_*` a la papelera con `mcp__Google_Drive__trash_file`.

No uses proxies de imágenes de terceros.

## Variedad de productos (pedido de Diego, 2026-10-16)
**PROHIBIDO peluches brainrot (handles "peluches-brainrot-...", Tung Tung, Lirili, Burlaloni, Chimpancini, Boneca Ambalabu,
Capuccino Assassino, etc.) en todas las artes nuevas desde 2026-10-17 hasta 2026-10-31.** Se puede volver a usarlos desde
2026-11-01, y entonces como máximo 1 de cada 4 historias y nunca dos el mismo día.
Prioriza variedad: bisutería, accesorios, útiles/esferos, juegos de mesa, Lego, blind boxes, charms, otros peluches que
no sean brainrot, etc. En domingo ("Peluches y juguetes") y lunes ("Novedades") busca alternativas que no sean brainrot.
Excepción ya aprobada: las artes del 2026-10-19 (ya programadas) quedan como están.

## Más juguetes (pedido de Diego, 2026-10-20)
Ahora hay más juguetes en Shopify: en las próximas artes, revisa el catálogo completo (ordena por fecha de creación, más recientes primero) y prioriza juguetes nuevos, no solo bisutería y papelería.

## Más spinners (pedido de Diego, 2026-10-26)
La próxima tanda de artes (la siguiente fecha objetivo libre después del 2026-10-29) debe incluir más spinners de fútbol (sets de 2 spinners y sets con cancha, handles "set-football-spinners-..." / "set-completo-con-cancha-football-spinner-..."), con piezas distintas a las ya usadas (ver registro.csv). Sigue siendo obligatorio que la historia 1 y la 2 sean productos distintos.

## Anti-duplicados en Metricool (pedido de Diego, 2026-11-07)
El 6-nov salió dos veces el reel de la pulsera Mano de Fátima (dos tandas lo programaron). Para cualquier tarea que publique:
1. **Antes de cada `createScheduledPost`**, consulta `getScheduledPosts` (brandId 7355030, timezone America/Guayaquil,
   rango = el día de publicación completo, `extendedRange: true`).
2. Si ya existe (programado o publicado) un post de la misma red y tipo para ese día con el mismo producto o el mismo
   archivo/tema, **no programes otro**. Avisa a Diego qué ya existe. Para cambiar algo ya programado usa
   `updateScheduledPost`, nunca un post nuevo.
3. Una sola `createScheduledPost` por pieza. Si da error, vuelve a consultar `getScheduledPosts` antes de reintentar
   (a veces sí quedó creada).

## Historias de Instagram con Windsor, no con Metricool (pedido de Diego, 2026-11-08)
**PRIORIDAD:** esta sección MANDA sobre el prompt de "Kimo tareas para 2 dias" (paso 7 y "AHORRO DE ZAPIER"). El plan gratis de Metricool solo publica 20 posts al mes por red, así que las historias de IG ya no pasan por ahí.
- En cada tarea "Publicar historias KIMO <F>", las historias de IG van con `mcp__Windsor_ai__execute_action` (cárgala con ToolSearch): connector `instagram`, action `create_story`, account `17841467127423464` (@kimo.ecu), params `{"image_url": "<URL>"}` o `{"video_url": "<URL>"}`. Publica al instante: la tarea ya corre a las 10:52, así que una llamada tras otra, en orden.
- URLs: imágenes con raw.githubusercontent.com. Video con jsDelivr fijado al commit, porque raw lo sirve como octet-stream: `https://cdn.jsdelivr.net/gh/ddonoso1992-eng/Kimo-historias@<sha completo del commit que subió el video>/historias/F_video.mp4`. Los links de Drive no sirven para Windsor.
- Una sola llamada por pieza, sin reintentos. Si una falla, para las que siguen y avisa a Diego con el error exacto. No uses Metricool de respaldo para historias sin que él lo diga.
- TikTok sigue en Metricool y cuenta para el tope de 20. Antes de programar en Metricool cuenta los publicados del mes con `getScheduledPosts` (cada red suma aparte); si ya van 20, no programes y avisa a Diego.

## Reels de Instagram con el publicador propio, no con Metricool (pedido de Diego, 2026-11-08)
**Gratis y sin tope.** El workflow "Publicar en Instagram" corre cada 10 min y publica lo que esté en `programados/` cuando llega su hora (`tools/ig_publicar.py` explica el formato). Usa el secreto `IG_TOKEN` (KIMO bot, app kimo ventas).
- Para programar un reel: crea `programados/F_reel.json` con `fecha`, `tipo: "REEL"`, `archivo` (ruta en el repo), `texto`, `audio_id` o `cancion`, `volumen_musica`, `volumen_video`, y haz push. Sale con unos minutos de atraso.
- Para buscar la canción sin publicar: sube `programados/comprobar.json` con `{"busquedas": ["título"]}` y lee `programados/estado/ultima_comprobacion.json` (el campo `cuando` debe ser nuevo). Usa el `audio_id` que coincida; nunca publiques mudo.
- Anti-duplicados: si `F_reel.json` ya existe en `programados/` o en `en_proceso/`, `publicados/` o `errores/`, no crees otro; para cambiarlo edita el archivo mientras siga pendiente. No programes el mismo reel en Metricool.
- Resultado: `programados/publicados/` trae el enlace; `programados/errores/` trae el error exacto. No reintenta solo una publicación fallida.

## Reels con voz (= voz + música)
Si Diego aprueba "con voz", el reel lleva **voz Y música**, nunca solo una de las dos:
- Se programa SOLO el archivo `*_voz.mp4`, con la canción en tendencia,
  `volumen_musica: 25` (música de fondo) y `volumen_video: 100` (la voz).
- Antes de programar, confirma con `ffprobe -show_streams` que el archivo tiene pista de audio.
- Si Instagram no tiene la canción, NO lo publiques solo con voz: déjalo sin programar y avisa a Diego.

## Estilo editorial para TODAS las historias (pedido de Diego, 2026-11-07)
**PRIORIDAD:** esta sección MANDA sobre cualquier instrucción de diseño del prompt de la tarea "Kimo tareas para 2 dias" (pasos 3 y 4: plantillas kimo_historias.py producto/cta, botón de WhatsApp, "¡Última unidad!", alternar foto realista/fantasía). Lo demás del prompt (fecha objetivo, temas por día, GitHub, Drive, aprobación, publicación con Metricool) sigue igual.
- Las 2 historias van con foto de OpenAI (una por producto, primero A y luego B): selected_api `ChatGPTCLIAPI`, action `create_image_edit`, tool_name `chatgpt_openai_create_image_edit`, connection_id `02729133-591d-8a12-9e30-b6058483be5e`, params `{"image": "<foto Shopify>", "model": "gpt-image-1", "size": "1024x1536", "output_format": "jpeg", "results_number": 1, "prompt": "..."}`. Si el error dice que el modelo no existe (no se cobra), una vez con `gpt-image-1.5`. Guarda la imagen en `fotos_ia/F_<handle>_persona.jpg` (con persona) o `_escena.jpg`. La historia 1 lleva persona (manos/muñeca) cuando el producto lo permita.
Desde las artes del 2026-11-11, las 2 historias del día van en estilo **editorial, serio y elegante** (tipo Pandora/Mejuri), sin desesperación:
- Foto: una generación de OpenAI (create_image_edit) partiendo de la foto real de Shopify, producto en contexto real
  (muñeca/mano, cama, escritorio, mesa), luz natural cálida, tonos crema/neutros, tercio inferior despejado para texto.
  El producto debe quedar IDÉNTICO y a su TAMAÑO REAL (cuidado con las escalas).
- Arte: `python3 tools/historia_editorial.py FOTO salida.jpg "ETIQUETA" "Titular" "Producto  ·  $precio" "Respóndenos para separarlo/a"`.
  La plantilla trae fuentes (tools/fonts), logo y el aviso obligatorio en letra pequeña:
  "Imagen referencial. Antes de comprar, solicita una foto real del producto: el tamaño y las proporciones pueden variar según el ángulo de la fotografía."
- PROHIBIDO lenguaje de urgencia agresiva ("¡Última unidad!", "¡Apúrate!", "corre", contadores, precios tachados).
  Titulares cortos y tranquilos (máx. 5 palabras): "Un detalle que se queda", "Nuevo en KIMO", "Para regalar esta Navidad".
- Costo: UNA sola generación por imagen, nunca en paralelo, sin reintentos (~$0,02 c/u). Si falla, usa la foto de Shopify con
  `kimo_historias.py producto` y avísale a Diego qué falló.

## Imágenes generadas con IA en Shopify (pedido de Diego, 2026-11-08)
- Toda imagen generada con IA (OpenAI) que se suba a un producto de Shopify va como **2.ª foto** (la foto real queda 1.ª).
  Súbela con `productUpdate(product:{id}, media:[{originalSource:<URL raw de GitHub fotos_ia/...>, mediaContentType: IMAGE, alt}])`
  (usa la foto limpia, sin textos de la historia) y luego `productReorderMedia` para dejarla en posición 1 (índice, la 2.ª).
- En la descripción del producto agrega (si no está ya) al final la MISMA nota que llevan las historias, exacta: `<p><em>Imagen referencial. Antes de comprar, solicita una foto real del producto: el tamaño y las proporciones pueden variar según el ángulo de la fotografía.</em></p>`
- Cuando el producto sea pulsera/joya italiana, genera la imagen con la foto real de la pulsera y del charm como referencia: eslabones cuadrados (~9x9 mm), pegados, y el charm como un eslabón más.
