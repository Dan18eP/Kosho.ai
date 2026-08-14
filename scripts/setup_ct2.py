"""Setup idempotente de modelos CTranslate2 OPUS-MT para Kosho.ai.

Descarga el modelo Marian OPUS-MT para el par indicado y lo convierte a
formato CTranslate2 (int8). Si el modelo ya está convertido no hace nada.
No requiere claves ni pagos; solo `pip install ctranslate2 sentencepiece`.

Pares:
    en-ja  -> models/enja_ct2   (motor principal del Optimizador)
    en-es  -> models/enes_ct2   (traducción de ensayos/contextos al español)

Uso:
    python scripts/setup_ct2.py [--pair en-ja] [--pair en-es] [--all]
"""

import argparse
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"

# URLs de OPUS-MT (object.pouta.csc.fi). Se prueban en orden por si alguna
# deja de estar disponible; cada par debe declarar al menos una.
PAIRS: dict[str, dict] = {
    "en-ja": {
        "model_dir": "enja",
        "output_dir": "enja_ct2",
        "zip": "opus-enja.zip",
        "urls": [
            "https://object.pouta.csc.fi/OPUS-MT-models/en-jap/opus-2020-01-08.zip",
        ],
    },
    "en-es": {
        "model_dir": "enes",
        "output_dir": "enes_ct2",
        "zip": "opus-enes.zip",
        "urls": [
            "https://object.pouta.csc.fi/Tatoeba-MT-models/eng-spa/opus-2021-02-19.zip",
            "https://object.pouta.csc.fi/Tatoeba-MT-models/eng-spa/opus+bt-2021-04-10.zip",
        ],
    },
}


def _download_first(model_dir: Path, zip_path: Path, urls: list[str]) -> bool:
    """Descarga la primera URL que responde; devuelve False si todas fallan."""
    for url in urls:
        try:
            print(f"[setup_ct2] Probando {url} ...")
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status < 400:
                    urlret = url
                    break
        except Exception:  # noqa: BLE001, S112 - probar la siguiente URL (opcional)
            continue
    else:
        print("[setup_ct2] Ninguna URL del par respondió correctamente.")
        return False

    print(f"[setup_ct2] Descargando {urlret}")
    urllib.request.urlretrieve(urlret, zip_path)
    return True


def setup_pair(name: str) -> bool:
    cfg = PAIRS[name]
    model_dir = MODELS_DIR / cfg["model_dir"]
    output_dir = MODELS_DIR / cfg["output_dir"]
    zip_path = model_dir / cfg["zip"]

    if (output_dir / "model.bin").exists():
        print(f"[setup_ct2] Modelo {name} ya listo en {output_dir} (omitido).")
        return True

    model_dir.mkdir(parents=True, exist_ok=True)
    if not (model_dir / "source.spm").exists():
        if not zip_path.exists() and not _download_first(
            model_dir, zip_path, cfg["urls"]
        ):
            return False
        print("[setup_ct2] Extrayendo...")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(model_dir)
        zip_path.unlink(missing_ok=True)

    converter = shutil.which("ct2-opus-mt-converter")
    if not converter:
        converter = str(
            ROOT / "backend" / ".venv" / "Scripts" / "ct2-opus-mt-converter.exe"
        )
    print(f"[setup_ct2] Convirtiendo {name} a CTranslate2 (int8)...")
    subprocess.run(
        [
            converter,
            "--model_dir",
            str(model_dir),
            "--output_dir",
            str(output_dir),
            "--quantization",
            "int8",
        ],
        check=True,
    )
    print(f"[setup_ct2] Listo: {output_dir}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pair",
        action="append",
        choices=list(PAIRS),
        default=None,
        help="Par de idiomas a instalar (repetible).",
    )
    parser.add_argument("--all", action="store_true", help="Instala todos los pares.")
    args = parser.parse_args(argv)

    targets = list(PAIRS) if args.all else (args.pair or ["en-ja"])
    ok = True
    for pair in targets:
        ok = setup_pair(pair) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
