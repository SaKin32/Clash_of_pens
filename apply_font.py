"""Run once from the project root: makes every screen use load_font() instead of the default font."""

import pathlib

for path in sorted(pathlib.Path("game").glob("*.py")):
    if path.name == "assets.py":
        continue
    text = path.read_text(encoding="utf-8")
    if "pygame.font.Font(None, " not in text:
        continue
    text = text.replace("pygame.font.Font(None, ", "load_font(")
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("from game.assets import"):
            if "load_font" not in line:
                lines[i] = line + ", load_font"
            break
    else:
        index = lines.index("import pygame")
        lines.insert(index + 1, "from game.assets import load_font")
    path.write_text("\n".join(lines), encoding="utf-8")
    print("updated", path)