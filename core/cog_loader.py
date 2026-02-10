import importlib
import pkgutil
from typing import List
import logging

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Cog Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

log = logging.getLogger("utilitybot")

def discover_cogs(*package_names: str) -> List[str]:
    cogs: list[str] = []

    for package_name in package_names:
        try:
            package = importlib.import_module(package_name)
        except Exception as e:
            log.error("Failed to import package %s: %s", package_name, e)
            continue

        for module_info in pkgutil.walk_packages(
            package.__path__,
            prefix=f"{package.__name__}."
        ):
            try:
                module = importlib.import_module(module_info.name)
            except Exception:
                log.exception("Failed to import module %s", module_info.name)
                continue

            if callable(getattr(module, "setup", None)):
                cogs.append(module_info.name)
            else:
                log.debug("Skipped (no setup): %s", module_info.name)

    return sorted(cogs)