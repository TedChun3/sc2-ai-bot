from __future__ import annotations

import importlib.util
import inspect
import sys
import uuid
from pathlib import Path

from sc2.bot_ai import BotAI

PREFERRED_CLASS_NAMES = (
    "CompetitiveBot",
    "ProtossBot",
    "TerranBot",
    "ZergBot",
)


def load_bot_module(bot_file: str | Path):
    path = Path(bot_file).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Bot file not found: {path}")

    module_name = f"uploaded_strategy_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to create import spec for {path}")

    module = importlib.util.module_from_spec(spec)
    original_sys_path = list(sys.path)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original_sys_path

    return module


def discover_bot_class(bot_file: str | Path, class_name: str | None = None) -> type[BotAI]:
    module = load_bot_module(bot_file)

    if class_name is not None:
        candidate = getattr(module, class_name, None)
        if candidate is None:
            raise ValueError(f"Class {class_name!r} was not found in {bot_file}")
        if not inspect.isclass(candidate) or not issubclass(candidate, BotAI):
            raise TypeError(f"Class {class_name!r} is not a BotAI subclass")
        return candidate

    candidates = [
        obj
        for obj in vars(module).values()
        if inspect.isclass(obj)
        and issubclass(obj, BotAI)
        and obj is not BotAI
        and obj.__module__ == module.__name__
    ]

    if not candidates:
        raise ValueError(f"No BotAI subclass found in {bot_file}")

    if len(candidates) == 1:
        return candidates[0]

    for preferred_name in PREFERRED_CLASS_NAMES:
        for candidate in candidates:
            if candidate.__name__ == preferred_name:
                return candidate

    candidates.sort(key=lambda candidate: candidate.__name__)
    return candidates[0]


def instantiate_bot(bot_file: str | Path, class_name: str | None = None) -> BotAI:
    bot_class = discover_bot_class(bot_file, class_name=class_name)
    return bot_class()
