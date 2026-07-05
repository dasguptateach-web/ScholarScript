import importlib
import inspect
from pathlib import Path
from typing import List, Any


class ScholarScriptPlugin:
    """Base class for all ScholarScript plugins."""

    name: str = "base"
    version: str = "1.0.0"

    def on_build_start(self, config: Any, items: List[Any]) -> None:
        pass

    def on_content_loaded(self, items: List[Any]) -> None:
        pass

    def on_page_render(self, template_name: str, context: dict) -> dict:
        return context

    def on_build_end(self, public_dir: Path) -> None:
        pass


def load_plugins(plugin_dir: Path, enabled_names: List[str]) -> List[ScholarScriptPlugin]:
    """Dynamically load enabled plugins from the plugins directory."""
    plugins = []
    if not plugin_dir.exists():
        return plugins
    sys_path_saved = list(__import__("sys").path)
    import sys
    sys.path.insert(0, str(plugin_dir))
    try:
        for f in plugin_dir.glob("*.py"):
            if f.stem.startswith("_"):
                continue
            if enabled_names and f.stem not in enabled_names:
                continue
            try:
                mod = importlib.import_module(f.stem)
                for _, obj in inspect.getmembers(mod, inspect.isclass):
                    if issubclass(obj, ScholarScriptPlugin) and obj is not ScholarScriptPlugin:
                        instance = obj()
                        plugins.append(instance)
            except Exception:
                pass
            finally:
                if f.stem in sys.modules:
                    del sys.modules[f.stem]
    finally:
        sys.path = sys_path_saved
    return plugins
