import importlib
import importlib.util
import pkgutil
import logging

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Cog Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

log = logging.getLogger("Utility Bot")

def discover_cogs(*package_names: str, priority: list[str] | None = None) -> list[str]:
    seen: set[str] = set()
    cogs: list[str] = []
    for package_name in package_names:
        try:
            package = importlib.import_module(package_name)
        except Exception as e:
            log.error("Failed to import package %s: %s", package_name, e)
            continue

        if callable(getattr(package, "setup", None)) and package_name not in seen:
            seen.add(package_name)
            cogs.append(package_name)

        for module_info in pkgutil.walk_packages(
            package.__path__,
            prefix=f"{package.__name__}."
        ):
            if module_info.name in seen or module_info.name.split('.')[-1].startswith('_'):
                continue

            spec = importlib.util.find_spec(module_info.name)
            if spec and spec.origin and spec.origin.endswith('.py'):
                try:
                    with open(spec.origin, 'r', encoding='utf-8') as f:
                        if "def setup" in f.read():
                            seen.add(module_info.name)
                            cogs.append(module_info.name)
                except Exception:
                    continue

    if priority:
        priority_set = set(priority)
        ordered_cogs = [m for m in priority if m in seen]
        remaining_cogs = [m for m in cogs if m not in priority_set]
        cogs = ordered_cogs + sorted(remaining_cogs)
    else:
        cogs = sorted(cogs)
    return cogs