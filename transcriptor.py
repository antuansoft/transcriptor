import whisper
import json
import torch
import os
import re
import time
import csv
from docx import Document
from datetime import datetime, timedelta

# --- Seguridad: extensiones permitidas ---
EXTENSIONES_PERMITIDAS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.mp4'}

# Velocidades aproximadas de procesamiento por modelo (segundos de audio por segundo real)
# Medidas empíricas con GPU mid-range
VELOCIDAD_MODELO = {
    "tiny":   30,
    "base":   20,
    "small":  12,
    "medium":  6,
    "large":   3
}

STATS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats.csv")
STATS_CABECERA = ["fecha", "dispositivo", "modelo", "archivo", "extension",
                  "duracion_seg", "duracion_fmt", "estimado_seg", "estimado_fmt",
                  "real_seg", "real_fmt", "velocidad"]
MIN_MUESTRAS_HISTORICO = 3

def validar_archivo(file_path: str) -> bool:
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        raise ValueError(f"Extensión no permitida: {ext}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")
    return True

def sanitizar_nombre(file_path: str) -> str:
    nombre = os.path.basename(file_path)
    nombre = re.sub(r'[^\w\-.]', '_', nombre)
    return os.path.splitext(nombre)[0]

def format_timestamp(seconds: float) -> str:
    td = timedelta(seconds=seconds)
    h, m, s = str(td).split(':')
    if '.' in s:
        s, ms = s.split('.')
        ms = ms[:3]
    else:
        ms = '000'
    return f"{int(h):02}:{int(m):02}:{s}.{ms}"

def format_duracion(seconds: float) -> str:
    """Convierte segundos a formato legible Xm Ys"""
    m = int(seconds // 60)
    s = int(seconds % 60)
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"

def obtener_duracion_audio(file_path: str) -> float:
    """Obtiene la duración del audio en segundos usando ffprobe"""
    import subprocess
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())
    except Exception:
        return None

def leer_velocidad_historica(dispositivo: str, modelo: str) -> float | None:
    """Devuelve la velocidad media real (audio_seg/real_seg) para este dispositivo+modelo.
    Requiere al menos MIN_MUESTRAS_HISTORICO entradas. Devuelve None si no hay suficientes datos."""
    if not os.path.exists(STATS_PATH):
        return None
    muestras = []
    with open(STATS_PATH, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if fila["dispositivo"] == dispositivo and fila["modelo"] == modelo:
                try:
                    muestras.append(float(fila["velocidad"]))
                except (ValueError, KeyError):
                    pass
    if len(muestras) >= MIN_MUESTRAS_HISTORICO:
        return sum(muestras) / len(muestras)
    return None

def estimar_tiempo(duracion_audio: float, modelo: str, velocidad_historica: float | None = None) -> float:
    """Estima el tiempo de procesamiento en segundos.
    Usa velocidad_historica si está disponible, si no el valor fijo del diccionario."""
    velocidad = velocidad_historica if velocidad_historica else VELOCIDAD_MODELO.get(modelo, 6)
    return duracion_audio / velocidad

def guardar_stats(dispositivo: str, modelo: str, archivo: str, extension: str,
                  duracion: float, estimado: float, real: float):
    """Añade una fila al CSV de estadísticas."""
    velocidad = duracion / real if real > 0 else 0
    nueva_fila = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dispositivo": dispositivo,
        "modelo": modelo,
        "archivo": archivo,
        "extension": extension,
        "duracion_seg": f"{duracion:.2f}",
        "duracion_fmt": format_duracion(duracion),
        "estimado_seg": f"{estimado:.2f}",
        "estimado_fmt": format_duracion(estimado),
        "real_seg": f"{real:.2f}",
        "real_fmt": format_duracion(real),
        "velocidad": f"{velocidad:.2f}",
    }
    escribir_cabecera = not os.path.exists(STATS_PATH)
    with open(STATS_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=STATS_CABECERA)
        if escribir_cabecera:
            writer.writeheader()
        writer.writerow(nueva_fila)
    print(f"  📊 Stats guardadas en: {STATS_PATH}")

def transcribe_audio(file_path: str, model) -> dict:
    """Transcribe con barra de progreso por segmentos"""
    import threading

    resultado = {}
    error = []

    # Hilo de progreso animado mientras transcribe
    stop_spinner = threading.Event()

    def spinner():
        chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        i = 0
        t0 = time.time()
        while not stop_spinner.is_set():
            elapsed = int(time.time() - t0)
            mm, ss = divmod(elapsed, 60)
            print(f"\r  {chars[i % len(chars)]} Procesando audio...  {mm:02}:{ss:02}", end="", flush=True)
            i += 1
            time.sleep(0.1)
        elapsed = int(time.time() - t0)
        mm, ss = divmod(elapsed, 60)
        print(f"\r  ✅ Audio procesado en {mm:02}:{ss:02}          ", flush=True)

    hilo = threading.Thread(target=spinner)
    hilo.start()

    try:
        resultado = model.transcribe(file_path)
    except Exception as e:
        error.append(e)
    finally:
        stop_spinner.set()
        hilo.join()

    if error:
        raise error[0]

    return resultado

def guardar_word(texto: str, output_path: str):
    doc = Document()
    doc.add_heading("Transcripción", level=1)
    doc.add_paragraph(texto)
    doc.save(output_path)
    print(f"  📄 Word guardado en: {output_path}")

def guardar_json(result: dict, output_path: str):
    segmentos = []
    for seg in result.get("segments", []):
        segmentos.append({
            "text": seg["text"].strip(),
            "start": seg["start"],
            "end": seg["end"],
            "start_timestamp": format_timestamp(seg["start"]),
            "end_timestamp": format_timestamp(seg["end"])
        })
    data = {"transcription": result.get("text", ""), "segments": segmentos}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"  📋 JSON guardado en: {output_path}")

def limpiar_archivos(*rutas):
    for ruta in rutas:
        if ruta and os.path.exists(ruta):
            os.remove(ruta)
            print(f"  🗑️  Archivo temporal eliminado: {ruta}")

def procesar_archivo(audio_path: str, model, modelo: str, device: str) -> float:
    """Transcribe un archivo y guarda Word, JSON y estadísticas. Devuelve el tiempo real."""
    extension = os.path.splitext(audio_path)[1].lower().lstrip(".")
    print(f"\n  Archivo     : {os.path.basename(audio_path)}")
    print(f"  Extensión   : {extension}")

    validar_archivo(audio_path)
    base_name = sanitizar_nombre(audio_path)
    carpeta = os.path.dirname(os.path.abspath(audio_path))
    word_out = os.path.join(carpeta, f"{base_name}_transcript.docx")
    json_out = os.path.join(carpeta, f"{base_name}_transcript.json")

    # Velocidad histórica para estimación ajustada
    velocidad_historica = leer_velocidad_historica(device.upper(), modelo)

    # Duración y estimación
    print("\n  Analizando archivo de audio...")
    duracion = obtener_duracion_audio(audio_path)
    if duracion:
        estimado = estimar_tiempo(duracion, modelo, velocidad_historica)
        print(f"  Duración audio  : {format_duracion(duracion)}")
        fuente = "histórico" if velocidad_historica else "estimado"
        print(f"  ⏱️  Tiempo estimado : ~{format_duracion(estimado)} ({fuente})")
    else:
        print("  ⚠️  No se pudo estimar la duración")

    # Transcripción
    print(f"\n  Iniciando transcripción...")
    t_inicio = time.time()
    result = transcribe_audio(audio_path, model)
    tiempo_real = time.time() - t_inicio

    # Guardado
    print("\n  Guardando archivos...")
    guardar_word(result.get("text", ""), word_out)
    guardar_json(result, json_out)

    # Resumen del archivo
    print("\n" + "-" * 60)
    if duracion:
        print(f"  Duración audio    : {format_duracion(duracion)}")
        print(f"  Tiempo estimado   : ~{format_duracion(estimado)}")
    print(f"  Tiempo real       : {format_duracion(tiempo_real)}")
    if duracion:
        print(f"  Velocidad         : {duracion / tiempo_real:.1f}x tiempo real")
    print(f"  Word → {word_out}")
    print(f"  JSON → {json_out}")
    print("-" * 60)

    # Guardar estadísticas
    if duracion:
        guardar_stats(device.upper(), modelo, os.path.basename(audio_path),
                      extension, duracion, estimado, tiempo_real)
    return tiempo_real

# --- Main ---
if __name__ == "__main__":
    import sys

    # Configuración inicial
    # Lista de archivos a procesar en orden. También se pueden pasar por línea de comandos:
    #   python transcriptor.py audio1.m4a audio2.mp3 ...  (si se pasan, sustituyen a esta lista)
    AUDIO_PATHS = [
        r"C:\Users\a.martinez.alfaya\OneDrive - Accenture\Desktop\tmp\2026-11-04-GHES-restaurar-certificado.m4a",
        r"C:\Users\a.martinez.alfaya\OneDrive - Accenture\Desktop\tmp\2026-11-03-SEP-343.m4a",
        r"C:\Users\a.martinez.alfaya\OneDrive - Accenture\Desktop\tmp\2026-11-04 - GEI-vs-Script.m4a",
    ]
    MODELO = "medium" # Opciones: tiny, base, small, medium, large

    if len(sys.argv) > 1:
        AUDIO_PATHS = sys.argv[1:]

    print("=" * 60)
    print("🎙️  TRANSCRIPTOR DE AUDIO - Whisper")
    print("=" * 60)

    device = "cuda" if torch.cuda.is_available() else "cpu" # Detecta automáticamente si hay GPU disponible si da error, fuerza a "cpu" con device = "cpu"
    print(f"\n  Dispositivo : {device.upper()}")
    print(f"  Modelo      : {MODELO}")
    print(f"  Archivos    : {len(AUDIO_PATHS)}")

    # Carga del modelo (una sola vez para todos los archivos)
    print(f"\n  Cargando modelo '{MODELO}'...")
    model = whisper.load_model(MODELO, device=device)
    print(f"  ✅ Modelo cargado")

    completados, fallidos = [], []
    t_lote = time.time()
    total = len(AUDIO_PATHS)

    for n, audio_path in enumerate(AUDIO_PATHS, start=1):
        print("\n" + "=" * 60)
        print(f"📁 [{n}/{total}] {os.path.basename(audio_path)}")
        print("=" * 60)
        try:
            procesar_archivo(audio_path, model, MODELO, device)
            completados.append(audio_path)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            fallidos.append((audio_path, str(e)))

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
