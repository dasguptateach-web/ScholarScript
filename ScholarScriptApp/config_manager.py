import json
import os
from pathlib import Path


CONFIG_FILE = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "ScholarScript" / "settings.json"


DEFAULT_CONFIG = {
    "github_token": "",
    "github_repo": "dasguptateach-web/ScholarScript",
    "github_branch": "main",
    "drop_folder": str(Path.home() / "Desktop" / "ScholarScript Drop"),
    "project_dir": "",
    "auto_deploy": True,
    "start_minimized": False,
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    try:
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            cfg.update(data)
    except Exception:
        pass
    return cfg


def save_config(cfg: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
