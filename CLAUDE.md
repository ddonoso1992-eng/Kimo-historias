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
