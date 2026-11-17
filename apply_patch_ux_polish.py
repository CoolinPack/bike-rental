from pathlib import Path

ROOT = Path(__file__).parent / "frontend" / "src"

# =============================================================
# 1. BikeForm.tsx — цена в VND с форматированием, число без стрелок
# =============================================================
form = ROOT / "pages" / "owner" / "BikeForm.tsx"
text = form.read_text(encoding="utf-8")

# При вводе цены — просто число, без преобразований. Метка уже «Цена за день, VND».
# Оставляем как есть. Цену пользователь вводит в VND вручную (500000).
# Ничего менять не надо, но убедимся, что в placeholder есть пример.

text = text.replace(
    'placeholder="500000"',
    'placeholder="например, 500000"',
)

# =============================================================
# 2. Catalog.tsx — цена в VND отформатирована
# (уже с formatMoney, но проверим что везде: «/день» с VND)
# =============================================================
catalog = ROOT / "pages" / "client" / "Catalog.tsx"
text = catalog.read_text(encoding="utf-8")

# Карточка: цена уже через formatMoney
# Оставляем как есть, тут всё ок.

# =============================================================
# 3. BikeBookingModal — считаем итог в VND с разделением разрядов
# =============================================================
booking = ROOT / "pages" / "client" / "BikeBookingModal.tsx"
text = booking.read_text(encoding="utf-8")

# Итог: сейчас `${total} VND`. Заменим на formatMoney
text = text.replace(
    '<span style={{ fontSize: 20, fontWeight: 700 }}>{total} VND</span>',
    '<span style={{ fontSize: 20, fontWeight: 700 }}>{formatMoney(total)}</span>',
)

# Строка «дней × цена» тоже пусть показывает VND
text = text.replace(
    '{days} ×{" "}\n            {bike.daily_price} VND',
    '{days} ×{" "}\n            {formatMoney(bike.daily_price)}',
)

# В конце файла — добавить formatMoney (если нет)
if "function formatMoney(" not in text:
    text = text.rstrip() + '''

function formatMoney(v: string | number): string {
  const n = Number(v);
  if (isNaN(n)) return "0 VND";
  return n.toLocaleString("ru-RU") + " VND";
}
'''

booking.write_text(text, encoding="utf-8")
print("✅ BikeBookingModal: цены в VND с разрядами")

# =============================================================
# 4. Requests.tsx — confirm на «Завершить»
# =============================================================
requests = ROOT / "pages" / "owner" / "Requests.tsx"
text = requests.read_text(encoding="utf-8")

# Добавляем confirm в complete
text = text.replace(
    '''  async function complete(id: number) {
    setActing(id);
    try {
      await api.post(`/client/bookings/${id}/complete`);
      reload();
      setSelected(null);
    } catch (e: any) {
      setError(e.message || "Не удалось завершить");
    } finally {
      setActing(null);
    }
  }''',
    '''  async function complete(id: number) {
    if (!confirm("Завершить аренду и вернуть байк в гараж?")) return;
    setActing(id);
    try {
      await api.post(`/client/bookings/${id}/complete`);
      reload();
      setSelected(null);
    } catch (e: any) {
      setError(e.message || "Не удалось завершить");
    } finally {
      setActing(null);
    }
  }''',
    1,
)

# Confirm на «Принять» — «Подтвердить заявку?»
text = text.replace(
    '''  async function accept(id: number) {
    setActing(id);
    try {
      await api.post(`/owner/requests/${id}/accept`);
      reload();
      setSelected(null);
    } catch (e: any) {
      setError(e.message || "Не удалось принять");
    } finally {
      setActing(null);
    }
  }''',
    '''  async function accept(id: number) {
    if (!confirm("Подтвердить заявку? Байк будет отмечен как арендованный.")) return;
    setActing(id);
    try {
      await api.post(`/owner/requests/${id}/accept`);
      reload();
      setSelected(null);
    } catch (e: any) {
      setError(e.message || "Не удалось принять");
    } finally {
      setActing(null);
    }
  }''',
    1,
)

requests.write_text(text, encoding="utf-8")
print("✅ Requests.tsx: confirm на accept/complete")

# =============================================================
# 5. History.tsx — confirm на «Завершить» и «Отменить»
# =============================================================
history = ROOT / "pages" / "client" / "History.tsx"
text = history.read_text(encoding="utf-8")

text = text.replace(
    '''  async function cancel(id: number) {
    setActingId(id);
    setActionError(null);
    try {''',
    '''  async function cancel(id: number) {
    if (!confirm("Отменить заявку?")) return;
    setActingId(id);
    setActionError(null);
    try {''',
    1,
)

text = text.replace(
    '''  async function complete(id: number) {
    setActingId(id);
    setActionError(null);
    try {''',
    '''  async function complete(id: number) {
    if (!confirm("Завершить аренду? Байк вернётся владельцу.")) return;
    setActingId(id);
    setActionError(null);
    try {''',
    1,
)

history.write_text(text, encoding="utf-8")
print("✅ History.tsx: confirm на cancel/complete")

# =============================================================
# 6. Кнопка «Назад» — добавляем в Layout (top-left) для страниц владельца/клиента
#    Открываем историю: window.history.back()
# =============================================================
layout = ROOT / "components" / "Layout.tsx"
text = layout.read_text(encoding="utf-8")

# Проверим, есть ли уже back-кнопка
if "app-back" not in text:
    # Заменяем интерфейс Layout — добавляем кнопку «Назад» в шапку
    # Найдём <Outlet /> и вставим перед ним
    text = text.replace(
        "<Outlet />",
        '''{typeof window !== "undefined" && window.history.length > 1 && (
        <button
          className="app-back"
          onClick={() => window.history.back()}
          aria-label="Назад"
        >
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none"
            stroke="currentColor" strokeWidth={2}
            strokeLinecap="round" strokeLinejoin="round">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
      )}
      <Outlet />''',
        1,
    )

    layout.write_text(text, encoding="utf-8")
    print("✅ Layout.tsx: кнопка «Назад»")

# =============================================================
# 7. theme.css — стиль для app-back
# =============================================================
css_path = ROOT / "styles" / "theme.css"
css = css_path.read_text(encoding="utf-8")

if ".app-back" not in css:
    css = css.rstrip() + """

/* === app-back === */
.app-back {
  all: unset;
  position: fixed;
  top: calc(12px + env(safe-area-inset-top, 0px));
  left: max(12px, calc(50% - 210px));
  z-index: 25;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--card);
  border: 1px solid var(--line-strong);
  color: var(--tx);
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: background 0.15s, transform 0.1s;
}

.app-back:hover {
  background: var(--bg);
}

.app-back:active {
  transform: scale(0.95);
}
"""

    css_path.write_text(css, encoding="utf-8")
    print("✅ theme.css: .app-back")

print("\nГотово. Перезапусти Vite и Ctrl+Shift+R.")