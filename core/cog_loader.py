import importlib
import pkgutil
from typing import List, Optional
import logging

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Cog Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

log = logging.getLogger("Utility Bot")

def discover_cogs(*package_names: str, priority: Optional[List[str]] = None) -> List[str]:
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

    if priority:
        priority_set = set(priority)
        ordered_cogs = [m for m in priority if m in cogs]
        remaining_cogs = [m for m in cogs if m not in priority_set]
        cogs = ordered_cogs + sorted(remaining_cogs)
    else:
        cogs = sorted(cogs)

    return cogs