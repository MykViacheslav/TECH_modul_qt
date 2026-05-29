from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


KEY_MODULE = "\u041c\u041e\u0414\u0423\u041b\u042c"
KEY_CODE = "\u0428\u0418\u0424\u0420"
KEY_LENGTH = "\u0414\u041b\u0418\u041d\u0410"
KEY_WIDTH = "\u0428\u0418\u0420\u0418\u041d\u0410"
KEY_HEIGHT = "\u0412\u042b\u0421\u041e\u0422\u0410"
KEY_INSERT = "\u0412\u0421\u0422\u0410\u0412\u041a\u0410"
KEY_ANGLE = "\u0423\u0413\u041e\u041b"
KEY_COORDINATE_SYSTEM = "\u0421\u041a"


@dataclass
class Constructor3DModule:
    index: int
    code: str
    length: float
    width: float
    height: float
    x: float
    y: float
    z: float = 0.0
    angle: float = 0.0
    coordinate_system: int = -1


def _fmt_num(value: float) -> str:
    value = float(value)
    if value.is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def build_model_list_ini(modules: list[Constructor3DModule]) -> str:
    lines: list[str] = []
    for i, module in enumerate(modules, 1):
        code = str(module.code or "").strip()
        if not code:
            continue
        lines.extend(
            [
                f"[{KEY_MODULE}{i}]",
                f"{KEY_CODE}={code}",
                f"{KEY_LENGTH}={_fmt_num(module.length)}",
                f"{KEY_WIDTH}={_fmt_num(module.width)}",
                f"{KEY_HEIGHT}={_fmt_num(module.height)}",
                f"{KEY_INSERT}={_fmt_num(module.x)} {_fmt_num(module.y)} {_fmt_num(module.z)}",
                f"{KEY_ANGLE}={_fmt_num(module.angle)}",
                f"{KEY_COORDINATE_SYSTEM}={int(module.coordinate_system)}",
                "",
            ]
        )
    return "\r\n".join(lines)


def save_model_list_ini(path: str | Path, modules: list[Constructor3DModule]) -> Path:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = build_model_list_ini(modules)
    out_path.write_text(text, encoding="cp1251", newline="")
    return out_path
