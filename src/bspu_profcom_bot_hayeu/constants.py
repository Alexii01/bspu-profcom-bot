from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent

ConfigPath = MODULE_DIR.parent / "data" / "token.ini"
TextPath = MODULE_DIR.parent / "data" / "text.json"
KeyboardsPath = MODULE_DIR.parent / "data" / "keyboards.json"
