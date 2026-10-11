"""KIMO - video corto 9:16 a partir de las 2 historias del día.
Uso: python3 kimo_video.py historia_1.jpg historia_2.jpg salida.mp4
Resultado: ~8 s, 1080x1920, 30 fps, H.264 + pista de audio AAC en silencio
(apto para historias de Instagram vía API y para subir a TikTok).
"""
import subprocess
import sys

h1, h2, out = sys.argv[1:4]
FPS = 30
D1, D2, FADE = 4.5, 4.0, 0.5

# zoom suave hacia el centro en cada imagen y fundido entre ambas
zoom = ("scale=2160:-1,zoompan=z='min(zoom+0.0009,1.08)':d={frames}:"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}")
filtro = (
    f"[0:v]{zoom.format(frames=int(D1 * FPS), fps=FPS)},format=yuv420p[a];"
    f"[1:v]{zoom.format(frames=int(D2 * FPS), fps=FPS)},format=yuv420p[b];"
    f"[a][b]xfade=transition=slideleft:duration={FADE}:offset={D1 - FADE}[v]"
)
cmd = [
    "ffmpeg", "-y", "-loglevel", "error",
    "-loop", "1", "-t", str(D1), "-i", h1,
    "-loop", "1", "-t", str(D2), "-i", h2,
    "-f", "lavfi", "-t", str(D1 + D2 - FADE), "-i", "anullsrc=r=44100:cl=stereo",
    "-filter_complex", filtro,
    "-map", "[v]", "-map", "2:a",
    "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS),
    "-crf", "23", "-preset", "medium", "-movflags", "+faststart",
    "-c:a", "aac", "-b:a", "128k", "-shortest", out,
]
subprocess.run(cmd, check=True)
print(out, "listo")
