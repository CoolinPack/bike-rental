from pathlib import Path

ROOT = Path(__file__).parent / "frontend" / "src"

css_path = ROOT / "styles" / "theme.css"
css = css_path.read_text(encoding="utf-8")

# Уменьшаем все max-width контейнеров до 440px
css = css.replace("max-width: 520px;", "max-width: 440px;")
css = css.replace("width: min(520px, 100%);", "width: min(440px, 100%);")

# Плюс немного уменьшаем внешние отступы в page
css = css.replace(
    """.page {
  padding: 16px 16px 96px;
  min-height: 100vh;
  max-width: 440px;
  margin: 0 auto;
  width: 100%;
}""",
    """.page {
  padding: 14px 14px 96px;
  min-height: 100vh;
  max-width: 420px;
  margin: 0 auto;
  width: 100%;
}""",
)

# app-header тоже под новую ширину
css = css.replace(
    """.app-header {
  max-width: 440px;
  margin: 0 auto;
  padding: 12px 16px 0;""",
    """.app-header {
  max-width: 420px;
  margin: 0 auto;
  padding: 12px 14px 0;""",
)

# Таб-бар под 420
css = css.replace(
    """.tab-bar,
.tabbar {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 0;
  z-index: 30;
  width: min(440px, 100%);""",
    """.tab-bar,
.tabbar {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 0;
  z-index: 30;
  width: min(420px, 100%);""",
)

css_path.write_text(css, encoding="utf-8")
print("✅ theme.css: контейнер 420px, отступы 14px")

print("\nГотово. Перезапусти Vite и F5.")