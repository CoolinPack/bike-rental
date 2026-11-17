from pathlib import Path

ROOT = Path(__file__).parent / "frontend" / "src"

# =============================================================
# 1. theme.css — тёплые границы, FAB, мягкие кнопки
# =============================================================
css_path = ROOT / "styles" / "theme.css"
css = css_path.read_text(encoding="utf-8")

# Заменяем цвет границ на тёплый
css = css.replace(
    "--line: rgba(128, 128, 128, 0.22);",
    "--line: rgba(120, 100, 80, 0.16);\n  --line-strong: rgba(120, 100, 80, 0.28);",
)

# В тёмной теме — тоже тёплый
css = css.replace(
    "--dk: #232a3a;\n    color-scheme: dark;",
    "--dk: #232a3a;\n    --line: rgba(180, 160, 140, 0.14);\n    --line-strong: rgba(180, 160, 140, 0.26);\n    color-scheme: dark;",
)

# Обновляем кнопки — мягкие тёплые границы
css = css.replace(
    """.btn.gh,
.btn-secondary {
  background: transparent;
  color: var(--tx);
  border: 1px solid var(--line);
}""",
    """.btn.gh,
.btn-secondary {
  background: var(--card);
  color: var(--tx);
  border: 1px solid var(--line-strong);
}
.btn.gh:hover,
.btn-secondary:hover {
  border-color: color-mix(in srgb, var(--ac) 40%, var(--line));
}""",
)

css = css.replace(
    """.btn.bad,
.btn-danger {
  background: transparent;
  color: var(--bad);
  border: 1px solid var(--line);
}""",
    """.btn.bad,
.btn-danger {
  background: var(--card);
  color: var(--bad);
  border: 1px solid color-mix(in srgb, var(--bad) 35%, var(--line));
}
.btn.bad:hover,
.btn-danger:hover {
  background: color-mix(in srgb, var(--bad) 8%, var(--card));
}""",
)

# Добавляем FAB в конец
css = css.rstrip() + """

/* === FAB (+ Добавить) === */
.fab {
  position: fixed;
  right: max(16px, calc(50% - 220px + 16px));
  bottom: calc(84px + env(safe-area-inset-bottom, 0px));
  z-index: 20;
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  padding: 0;
  background: var(--ac);
  color: var(--act);
  border: none;
  cursor: pointer;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.18),
              0 2px 4px rgba(0, 0, 0, 0.08);
  transition: transform 0.15s, box-shadow 0.15s;
}

.fab:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.22),
              0 2px 4px rgba(0, 0, 0, 0.1);
}

.fab:active {
  transform: scale(0.94);
}

.fab svg {
  width: 24px;
  height: 24px;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
}

/* === Финальные правки под ширину === */
.page {
  max-width: 520px;
}
.app-header {
  max-width: 520px;
}
.tab-bar,
.tabbar {
  width: min(520px, 100%);
}
"""

css_path.write_text(css, encoding="utf-8")
print("✅ theme.css: тёплые границы, FAB, мягкие кнопки")

# =============================================================
# 2. Garage.tsx — кнопка «+ Добавить» как FAB внизу справа
# =============================================================
garage = ROOT / "pages" / "owner" / "Garage.tsx"
text = garage.read_text(encoding="utf-8")

# Убираем старую кнопку из заголовка
text = text.replace(
    '''        <button
          className="btn"
          onClick={() => setCreating(true)}
          disabled={atLimit}
          title={atLimit ? "Достигнут лимит тарифа" : ""}
          style={atLimit ? { opacity: 0.5 } : {}}
        >
          + Добавить
        </button>''',
    "",
    1,
)

# Заголовок без кнопки — просто <h1>Гараж</h1>
text = text.replace(
    '''      <div
        className="row"
        style={{ justifyContent: "space-between", marginBottom: 8 }}
      >
        <h1 className="page-title" style={{ margin: 0 }}>
          Гараж
        </h1>
      </div>''',
    '''      <h1 className="page-title" style={{ margin: "0 0 8px" }}>
        Гараж
      </h1>''',
    1,
)

# Добавляем FAB в конце return (перед закрытием page)
text = text.replace(
    '''      {editing && (
        <OwnerBikeForm
          mode="edit"
          bike={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
        />
      )}
    </div>
  );
}''',
    '''      {editing && (
        <OwnerBikeForm
          mode="edit"
          bike={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
        />
      )}

      <button
        className="fab"
        onClick={() => setCreating(true)}
        disabled={atLimit}
        title={atLimit ? "Достигнут лимит тарифа" : "Добавить байк"}
        style={atLimit ? { opacity: 0.4, pointerEvents: "none" } : {}}
        aria-label="Добавить байк"
      >
        <svg viewBox="0 0 24 24">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>
    </div>
  );
}''',
    1,
)

garage.write_text(text, encoding="utf-8")
print("✅ Garage.tsx: FAB внизу справа")

# =============================================================
# 3. Expenses.tsx — FAB «+ Добавить»
# =============================================================
expenses = ROOT / "pages" / "owner" / "Expenses.tsx"
text = expenses.read_text(encoding="utf-8")

text = text.replace(
    '''      <div
        className="row"
        style={{ justifyContent: "space-between", marginBottom: 16 }}
      >
        <h1 className="page-title" style={{ margin: 0 }}>
          Расходы
        </h1>
        <button
          className="btn"
          onClick={() => setFormOpen(true)}
          disabled={bikes.length === 0}
        >
          + Добавить
        </button>
      </div>''',
    '''      <h1 className="page-title" style={{ margin: "0 0 8px" }}>
        Расходы
      </h1>''',
    1,
)

# Добавляем FAB перед закрытием
text = text.replace(
    '''      {formOpen && (
        <ExpenseFormModal
          bikes={bikes}
          onClose={() => setFormOpen(false)}
          onSaved={() => {
            setFormOpen(false);
            reload();
          }}
        />
      )}
    </div>
  );
}''',
    '''      {formOpen && (
        <ExpenseFormModal
          bikes={bikes}
          onClose={() => setFormOpen(false)}
          onSaved={() => {
            setFormOpen(false);
            reload();
          }}
        />
      )}

      <button
        className="fab"
        onClick={() => setFormOpen(true)}
        disabled={bikes.length === 0}
        title="Добавить расход"
        style={bikes.length === 0 ? { opacity: 0.4, pointerEvents: "none" } : {}}
        aria-label="Добавить расход"
      >
        <svg viewBox="0 0 24 24">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>
    </div>
  );
}''',
    1,
)

expenses.write_text(text, encoding="utf-8")
print("✅ Expenses.tsx: FAB")

# =============================================================
# 4. SuperParks (админ) — FAB
# =============================================================
parks = ROOT / "pages" / "superadmin" / "Parks.tsx"
text = parks.read_text(encoding="utf-8")

text = text.replace(
    '''      <div
        className="row"
        style={{ justifyContent: "space-between", marginBottom: 16 }}
      >
        <h1 className="page-title" style={{ margin: 0 }}>
          Парки
        </h1>
        <button className="btn" onClick={() => setCreating(true)}>
          + Добавить
        </button>
      </div>''',
    '''      <h1 className="page-title" style={{ margin: "0 0 8px" }}>
        Парки
      </h1>''',
    1,
)

text = text.replace(
    '''      {creating && (
        <ParkCreateModal
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            reload();
          }}
        />
      )}
    </div>
  );
}''',
    '''      {creating && (
        <ParkCreateModal
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            reload();
          }}
        />
      )}

      <button
        className="fab"
        onClick={() => setCreating(true)}
        aria-label="Добавить парк"
      >
        <svg viewBox="0 0 24 24">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>
    </div>
  );
}''',
    1,
)

parks.write_text(text, encoding="utf-8")
print("✅ Parks.tsx: FAB")

print("\nГотово. Перезапусти Vite и обнови браузер Ctrl+Shift+R.")