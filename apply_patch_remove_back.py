import re
from pathlib import Path

ROOT = Path(__file__).parent / "frontend" / "src"

# =============================================================
# 1. Layout.tsx — убираем app-back
# =============================================================
layout = ROOT / "components" / "Layout.tsx"
text = layout.read_text(encoding="utf-8")

# Удаляем блок с кнопкой app-back
text = re.sub(
    r"\{typeof window !== \"undefined\" && window\.history\.length > 1 && \(\s*<button[\s\S]*?</button>\s*\)\}\s*",
    "",
    text,
)

layout.write_text(text, encoding="utf-8")
print("✅ Layout.tsx: app-back удалён")

# =============================================================
# 2. theme.css — убираем стиль .app-back
# =============================================================
css_path = ROOT / "styles" / "theme.css"
css = css_path.read_text(encoding="utf-8")

css = re.sub(r"/\* === app-back === \*/[\s\S]*?\.app-back:active \{[^}]*\}", "", css)

css_path.write_text(css, encoding="utf-8")
print("✅ theme.css: .app-back удалён")

print("\nГотово. Перезапусти Vite и Ctrl+Shift+R.")