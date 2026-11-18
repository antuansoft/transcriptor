import argparse
import os
import subprocess
import textwrap
import time

import torch
import whisper

# --- Configuración ---
# Archivos a procesar si no se pasan por línea de comandos
AUDIO_PATHS = [
    # r"C:\ruta\a\pelicula.mkv",
]
MODELO = "medium"    # tiny | base | small | medium | large
IDIOMA = "en"        # Los subtítulos se generan siempre en inglés
MAX_CHARS = 42       # Caracteres máximos por línea de subtítulo
MAX_LINEAS = 2       # Líneas máximas por subtítulo

# --- Seguridad: extensiones permitidas ---
EXTENSIONES_PERMITIDAS = {
    '.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac', '.wma', '.opus',
    '.mp4', '.mkv', '.avi', '.mov', '.webm', '.wmv', '.m4v',
}

def validar_archivo(file_path: str) -> bool:
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        raise ValueError(f"Extensión no permitida: {ext}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")
    return True

def format_duracion(seconds: float) -> str:
    """Convierte segundos a formato legible Xh Ym Zs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"

def obtener_duracion_audio(file_path: str) -> float | None:
    """Obtiene la duración del archivo en segundos usando ffprobe"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())
    except Exception:
        return None

def format_timestamp_srt(seconds: float) -> str:
    """Formato SRT: HH:MM:SS,mmm (con coma en los milisegundos)"""
    total_ms = max(0, int(round(seconds * 1000)))
    h, resto = divmod(total_ms, 3_600_000)
    m, resto = divmod(resto, 60_000)
    s, ms = divmod(resto, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def obtener_palabras(segmento: dict) -> list[tuple[str, float, float]]:
    """Devuelve (palabra, inicio, fin) de un segmento.
    Usa los tiempos reales por palabra si existen; si no, los reparte
    proporcionalmente al número de caracteres dentro del segmento."""
    if segmento.get("words"):
        return [(w["word"].strip(), w["start"], w["end"])
                for w in segmento["words"] if w["word"].strip()]

    palabras = segmento["text"].split()
    if not palabras:
        return []
    inicio, fin = segmento["start"], segmento["end"]
    total_chars = sum(len(p) + 1 for p in palabras)
    resultado, acumulado = [], 0
    for p in palabras:
        t0 = inicio + (fin - inicio) * acumulado / total_chars
        acumulado += len(p) + 1
        t1 = inicio + (fin - inicio) * acumulado / total_chars
        resultado.append((p, t0, t1))
    return resultado

def construir_subtitulos(segmentos: list, max_chars: int, max_lineas: int) -> list[tuple[float, float, str]]:
    """Agrupa las palabras en subtítulos que no superen max_lineas líneas de max_chars caracteres.
    Devuelve una lista de (inicio, fin, texto)."""
    subtitulos = []

    def lineas(texto: str) -> list[str]:
        return textwrap.wrap(texto, width=max_chars)

    for seg in segmentos:
        actual, inicio, fin = [], None, None

        def cerrar():
            nonlocal actual, inicio, fin
            if actual:
                texto = "\n".join(lineas(" ".join(actual)))
                subtitulos.append((inicio, max(fin, inicio + 0.2), texto))
            actual, inicio, fin = [], None, None

        for palabra, t0, t1 in obtener_palabras(seg):
            if actual and len(lineas(" ".join(actual + [palabra]))) > max_lineas:
                cerrar()
            if not actual:
                inicio = t0
            actual.append(palabra)
            fin = t1
        cerrar()

    # Evita solapes entre subtítulos consecutivos
    for i in range(len(subtitulos) - 1):
        ini, fin, texto = subtitulos[i]
        siguiente_ini = subtitulos[i + 1][0]
        if fin > siguiente_ini:
            subtitulos[i] = (ini, max(siguiente_ini, ini + 0.05), texto)
    return subtitulos

def guardar_srt(subtitulos: list, output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        for n, (inicio, fin, texto) in enumerate(subtitulos, start=1):
            f.write(f"{n}\n")
            f.write(f"{format_timestamp_srt(inicio)} --> {format_timestamp_srt(fin)}\n")
            f.write(f"{texto}\n\n")
    print(f"  🎬 SRT guardado en: {output_path}")

def procesar_archivo(audio_path: str, model, device: str, args) -> int:
    """Transcribe un archivo y genera su .srt. Devuelve el número de subtítulos."""
    print(f"\n  Archivo     : {os.path.basename(audio_path)}")
    validar_archivo(audio_path)

    carpeta = args.output_dir or os.path.dirname(os.path.abspath(audio_path))
    os.makedirs(carpeta, exist_ok=True)
    nombre = os.path.splitext(os.path.basename(audio_path))[0]
    srt_out = os.path.join(carpeta, f"{nombre}.srt")
    if os.path.exists(srt_out):
        print(f"  ⚠️  Ya existe {os.path.basename(srt_out)}, se sobrescribirá")

    duracion = obtener_duracion_audio(audio_path)
    if duracion:
        print(f"  Duración    : {format_duracion(duracion)}")
    else:
        print("  ⚠️  No se pudo obtener la duración")

    print("\n  Iniciando transcripción...")
    t_inicio = time.time()
    result = model.transcribe(
        audio_path,
        language=IDIOMA,
        task="transcribe",
        word_timestamps=args.word_timestamps,
        condition_on_previous_text=False,  # reduce repeticiones y alucinaciones en archivos largos
        fp16=(device == "cuda"),
        verbose=False,
    )
    tiempo_real = time.time() - t_inicio

    subtitulos = construir_subtitulos(result.get("segments", []), args.max_chars, args.max_lines)
    if not subtitulos:
        raise ValueError("No se detectó voz en el archivo, no se generó ningún subtítulo")

    print("\n  Guardando archivo...")
    guardar_srt(subtitulos, srt_out)

    print("\n" + "-" * 60)
    if duracion:
        print(f"  Duración audio    : {format_duracion(duracion)}")
    print(f"  Tiempo real       : {format_duracion(tiempo_real)}")
    if duracion:
        print(f"  Velocidad         : {duracion / tiempo_real:.1f}x tiempo real")
    print(f"  Subtítulos        : {len(subtitulos)}")
    print(f"  SRT → {srt_out}")
    print("-" * 60)
    return len(subtitulos)

def parsear_argumentos():
    parser = argparse.ArgumentParser(
        description="Genera subtítulos .srt en inglés a partir de audio o vídeo con Whisper (local)."
    )
    parser.add_argument("archivos", nargs="*",
                        help="Archivos a procesar (si se omiten, se usa AUDIO_PATHS del script)")
    parser.add_argument("-m", "--model", default=MODELO,
                        choices=["tiny", "base", "small", "medium", "large"],
                        help=f"Modelo de Whisper (por defecto: {MODELO})")
    parser.add_argument("--device", choices=["cuda", "cpu"],
                        help="Fuerza el dispositivo (por defecto: cuda si está disponible, si no cpu)")
    parser.add_argument("-o", "--output-dir",
                        help="Carpeta de salida (por defecto: la misma carpeta que cada archivo)")
    parser.add_argument("--max-chars", type=int, default=MAX_CHARS,
                        help=f"Caracteres máximos por línea (por defecto: {MAX_CHARS})")
    parser.add_argument("--max-lines", type=int, default=MAX_LINEAS,
                        help=f"Líneas máximas por subtítulo (por defecto: {MAX_LINEAS})")
    parser.add_argument("--word-timestamps", action="store_true",
                        help="Usa tiempos por palabra para cortes más precisos (algo más lento)")
    return parser.parse_args()

# --- Main ---
if __name__ == "__main__":
    args = parsear_argumentos()
    rutas = args.archivos or AUDIO_PATHS
    if not rutas:
        print("❌ No hay archivos que procesar. Pásalos como argumentos o rellena AUDIO_PATHS en el script.")
        raise SystemExit(1)

    print("=" * 60)
    print("🎬  SUBTITLE GENERATOR - Whisper")
    print("=" * 60)

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n  Dispositivo : {device.upper()}")
    print(f"  Modelo      : {args.model}")
    print(f"  Idioma      : {IDIOMA}")
    print(f"  Archivos    : {len(rutas)}")

    # Carga del modelo (una sola vez para todos los archivos)
    print(f"\n  Cargando modelo '{args.model}'...")
    model = whisper.load_model(args.model, device=device)
    print("  ✅ Modelo cargado")

    completados, fallidos = [], []
    t_lote = time.time()
    total = len(rutas)

    for n, ruta in enumerate(rutas, start=1):
        print("\n" + "=" * 60)
        print(f"📁 [{n}/{total}] {os.path.basename(ruta)}")
        print("=" * 60)
        try:
            procesar_archivo(ruta, model, device, args)
            completados.append(ruta)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            fallidos.append((ruta, str(e)))

    # Resumen final del lote
    print("\n" + "=" * 60)
    print("✅  PROCESO FINALIZADO")
    print("=" * 60)
    print(f"  Completados : {len(completados)}/{total}")
    print(f"  Tiempo total: {format_duracion(time.time() - t_lote)}")
    if fallidos:
        print(f"  Con error   : {len(fallidos)}")
        for ruta, motivo in fallidos:
            print(f"    - {os.path.basename(ruta)}: {motivo}")
    print("=" * 60)
