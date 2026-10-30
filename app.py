"""Tradutor de screenshots para jogos.

Observa uma pasta, extrai texto em inglês da imagem e exibe uma tradução em
português em uma janela separada.
"""

from __future__ import annotations

import ctypes
import json
import queue
import sys
import threading
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any

import pytesseract
import tkinter as tk
from deep_translator import MyMemoryTranslator
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from tkinter import scrolledtext
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
DEFAULT_CONFIG: dict[str, Any] = {
    "screenshots_folder": "",
    "tesseract_cmd": r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
    "ocr_language": "eng",
    "monitor_number": 2,
    "window_width": 720,
    "window_height": 520,
    "always_on_top": True,
    "preprocess_image": True,
    "minimum_text_length": 2,
    "translation_provider": "mymemory",
    "delete_after_processing": True,
    "only_process_files_created_after_start": True,
}


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Configuração criada em: {CONFIG_PATH}")
        print("Edite screenshots_folder e, se necessário, tesseract_cmd. Depois execute novamente.")
        sys.exit(0)

    try:
        config = {**DEFAULT_CONFIG, **json.loads(CONFIG_PATH.read_text(encoding="utf-8"))}
    except json.JSONDecodeError as error:
        raise SystemExit(f"config.json inválido: {error}") from error

    folder = Path(config["screenshots_folder"]).expanduser()
    if not config["screenshots_folder"] or not folder.is_dir():
        raise SystemExit(
            "Defina uma pasta válida em screenshots_folder no arquivo config.json. "
            f"Arquivo: {CONFIG_PATH}"
        )
    config["screenshots_folder"] = folder
    return config


def monitor_rect(monitor_number: int) -> tuple[int, int, int, int]:
    """Retorna a área do monitor (1 = principal). Usa Win32 sem dependências extras."""
    if sys.platform != "win32":
        return (0, 0, 1920, 1080)

    monitors: list[tuple[int, int, int, int]] = []
    callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HANDLE, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
    )

    def callback(_monitor: int, _hdc: int, rect: Any, _data: int) -> bool:
        monitors.append((rect.contents.left, rect.contents.top, rect.contents.right, rect.contents.bottom))
        return True

    ctypes.windll.user32.EnumDisplayMonitors(0, 0, callback_type(callback), 0)
    index = monitor_number - 1
    if 0 <= index < len(monitors):
        return monitors[index]
    return monitors[0] if monitors else (0, 0, 1920, 1080)


def extract_text(image_path: Path, config: dict[str, Any]) -> str:
    """Aumenta contraste/tamanho antes do OCR, o que ajuda em legendas de jogos."""
    with Image.open(image_path) as source:
        image = source.convert("L")
        if config["preprocess_image"]:
            image = ImageOps.autocontrast(image)
            image = ImageEnhance.Contrast(image).enhance(1.8)
            image = image.resize((image.width * 2, image.height * 2))
            image = image.filter(ImageFilter.SHARPEN)
        text = pytesseract.image_to_string(image, lang=config["ocr_language"], config="--psm 6")
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def translate(text: str) -> str:
    """Traduz usando MyMemory; cada bloco aceita até 500 caracteres."""
    translator = MyMemoryTranslator(source="en-US", target="pt-BR")
    # Divide no espaço mais próximo para não cortar palavras. Um screenshot comum
    # cabe em uma única chamada; imagens muito textuais são processadas aos poucos.
    blocks: list[str] = []
    remaining = text.strip()
    while remaining:
        if len(remaining) <= 480:
            blocks.append(remaining)
            break
        split_at = remaining.rfind(" ", 0, 480)
        split_at = split_at if split_at > 0 else 480
        blocks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip()

    output: list[str] = []
    for index, block in enumerate(blocks):
        for attempt in range(3):
            try:
                output.append(translator.translate(block))
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
        # Evita excesso de chamadas caso uma imagem excepcionalmente grande precise de blocos.
        if index < len(blocks) - 1:
            time.sleep(1.2)
    return "\n".join(output)


class ScreenshotHandler(FileSystemEventHandler):
    def __init__(self, incoming: queue.Queue[Path]) -> None:
        self.incoming = incoming
        self.last_path: Path | None = None
        self.last_time = 0.0

    def on_created(self, event: Any) -> None:
        if not event.is_directory:
            self._submit(Path(event.src_path))

    def on_moved(self, event: Any) -> None:
        if not event.is_directory:
            self._submit(Path(event.dest_path))

    def _submit(self, path: Path) -> None:
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return
        now = time.monotonic()
        if path == self.last_path and now - self.last_time < 2:
            return
        self.last_path, self.last_time = path, now
        self.incoming.put(path)


class TranslatorApp:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        # Marca o início da sessão. Arquivos anteriores nunca devem ser afetados.
        self.started_at = time.time()
        self.incoming: queue.Queue[Path] = queue.Queue()
        self.results: queue.Queue[tuple[str, str, str]] = queue.Queue()

        self.root = tk.Tk()
        self.root.title("Tradutor do Jogo")
        self.root.configure(bg="#171a21")
        self.root.attributes("-topmost", bool(config["always_on_top"]))
        self.place_window()
        self.build_ui()

        self.observer = Observer()
        self.observer.schedule(ScreenshotHandler(self.incoming), str(config["screenshots_folder"]), recursive=False)
        self.observer.start()
        threading.Thread(target=self.worker, daemon=True).start()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(150, self.show_results)

    def place_window(self) -> None:
        left, top, right, bottom = monitor_rect(int(self.config["monitor_number"]))
        width, height = int(self.config["window_width"]), int(self.config["window_height"])
        x = left + max(0, ((right - left) - width) // 2)
        y = top + max(0, ((bottom - top) - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def build_ui(self) -> None:
        title = tk.Label(self.root, text="TRADUTOR DO JOGO", fg="#66c0f4", bg="#171a21", font=("Segoe UI", 15, "bold"))
        title.pack(pady=(14, 4))
        self.status = tk.Label(self.root, text=f"Observando: {self.config['screenshots_folder']}", fg="#a5b2bd", bg="#171a21", wraplength=660)
        self.status.pack(padx=20, pady=(0, 8))

        panel = tk.Frame(self.root, bg="#171a21")
        panel.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        panel.columnconfigure((0, 1), weight=1)
        panel.rowconfigure(1, weight=1)
        tk.Label(panel, text="TEXTO DETECTADO", fg="#a5b2bd", bg="#171a21").grid(row=0, column=0, sticky="w")
        tk.Label(panel, text="TRADUÇÃO", fg="#66c0f4", bg="#171a21").grid(row=0, column=1, sticky="w", padx=(10, 0))
        self.original = self.text_box(panel)
        self.original.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self.translated = self.text_box(panel)
        self.translated.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(4, 0))

    @staticmethod
    def text_box(parent: tk.Misc) -> scrolledtext.ScrolledText:
        return scrolledtext.ScrolledText(parent, wrap="word", bg="#0e1118", fg="#e8f1f8", insertbackground="white", relief="flat", font=("Segoe UI", 11), padx=10, pady=10)

    def worker(self) -> None:
        while True:
            path = self.incoming.get()
            # Steam às vezes cria o arquivo antes de terminar de gravá-lo.
            time.sleep(0.7)
            try:
                if self.config["only_process_files_created_after_start"]:
                    if path.stat().st_mtime < self.started_at:
                        # Pode acontecer se OneDrive sincronizar um arquivo antigo após abrir o programa.
                        continue
                text = extract_text(path, self.config)
                if len(text) < int(self.config["minimum_text_length"]):
                    self.results.put(("Nenhum texto legível foi encontrado.", "", path.name))
                    continue
                translated = translate(text)
                self.results.put((text, translated, path.name))
                if self.config["delete_after_processing"]:
                    path.unlink(missing_ok=True)
            except Exception as error:  # mantém o observador ativo após falhas pontuais
                self.results.put((f"Erro ao processar a imagem:\n{error}", "", path.name))

    def show_results(self) -> None:
        try:
            while True:
                original, translated, filename = self.results.get_nowait()
                for widget, value in ((self.original, original), (self.translated, translated)):
                    widget.delete("1.0", tk.END)
                    widget.insert("1.0", value)
                suffix = " — imagem apagada" if self.config["delete_after_processing"] else ""
                self.status.config(text=f"Última imagem: {filename}{suffix}")
        except queue.Empty:
            pass
        self.root.after(150, self.show_results)

    def close(self) -> None:
        self.observer.stop()
        self.observer.join(timeout=2)
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    config = load_config()
    command = Path(config["tesseract_cmd"])
    if not command.exists():
        raise SystemExit(f"Tesseract não encontrado em: {command}\nInstale-o ou ajuste tesseract_cmd no config.json.")
    pytesseract.pytesseract.tesseract_cmd = str(command)
    TranslatorApp(config).run()


if __name__ == "__main__":
    main()
