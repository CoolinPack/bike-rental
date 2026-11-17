import re
from pathlib import Path

ROOT = Path(__file__).parent / "frontend" / "src"

# =============================================================
# 1. Layout.tsx — убираем app-header с ролью и парком
# =============================================================
layout_path = ROOT / "components" / "Layout.tsx"
text = layout_path.read_text(encoding="utf-8")

# Убираем весь блок {me && (<div className="app-header">...)}
text = re.sub(
    r"\{me && \(\s*<div className=\"app-header\"[\s\S]*?</div>\s*\)\}",
    "",
    text,
)

# Убираем useAuth и me, если больше не используются
text = text.replace(
    'import { useAuth } from "../store/auth";\n',
    "",
)
text = text.replace(
    "  const { me } = useAuth();\n",
    "",
)

layout_path.write_text(text, encoding="utf-8")
print("✅ Layout.tsx: app-header удалён")

# =============================================================
# 2. Garage.tsx — убираем «N из M байков · Про» и warning-плашку
# =============================================================
garage = ROOT / "pages" / "owner" / "Garage.tsx"
text = garage.read_text(encoding="utf-8")

# Убираем строку счётчика
text = re.sub(
    r"\{profile && \(\s*<div\s+className=\"muted\"\s+style=\{\{\s*fontSize:\s*13,\s*marginBottom:\s*12\s*\}\}\s*>\s*\{bikes\.length\} из \{profile\.bikes_limit\}.*?</div>\s*\)\}",
    "",
    text,
    flags=re.DOTALL,
)

# Убираем блок с "Достигнут лимит тарифа"
text = re.sub(
    r"\{showLimitWarning && \(\s*<div[\s\S]*?</div>\s*\)\}",
    "",
    text,
)

# Убираем переменные showLimitWarning
text = text.replace(
    "  const showLimitWarning = atLimit && profile?.subscription_plan === \"start\";\n",
    "",
)

garage.write_text(text, encoding="utf-8")
print("✅ Garage.tsx: счётчик и warning удалены")

# =============================================================
# 3. Profile.tsx — оставляем как есть, это профиль
# =============================================================
# (там информация о подписке уместна — пользователь заходит специально)

# =============================================================
# 4. Убираем эмодзи-«×» из кнопок закрытия (это символ, но на всякий)
#    И icon-эмодзи из FAB и заголовков, если где-то остались
# =============================================================
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "\uFE0F"
    "]+",
    flags=re.UNICODE,
)

count = 0
for tsx in ROOT.rglob("*.tsx"):
    if "icons.tsx" in tsx.name:
        continue
    try:
        content = tsx.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    new_content, n = EMOJI_PATTERN.subn("", content)
    if n > 0:
        new_content = re.sub(r"  +", " ", new_content)
        tsx.write_text(new_content, encoding="utf-8")
        count += n
print(f"✅ Убрано эмодзи в .tsx: {count}")

print("\nГотово. Перезапусти Vite и обнови браузер Ctrl+Shift+R.")