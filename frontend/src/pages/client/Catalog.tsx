import { useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import { BikeItem } from "../../types";
import { BikeDetailsModal } from "./BikeDetailsModal";

type Status = "available" | "rented" | "maintenance";

const STATUS_LABEL: Record<Status, string> = {
  available: "Свободен",
  rented: "В аренде",
  maintenance: "На ТО",
};

const STATUS_CLASS: Record<Status, string> = {
  available: "badge-available",
  rented: "badge-rented",
  maintenance: "badge-maintenance",
};

const CC_OPTIONS = [50, 125, 150, 180, 200];
const PRICE_MAX = 1_500_000;

export function ClientCatalogPage() {
  const [bikes, setBikes] = useState<BikeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [priceFrom, setPriceFrom] = useState(0);
  const [license, setLicense] = useState<"any" | "yes" | "no">("any");
  const [ccFilter, setCcFilter] = useState<number | null>(null);

  const [selectedBike, setSelectedBike] = useState<BikeItem | null>(null);

  function reload() {
    setLoading(true);
    api
      .get<{ items: BikeItem[] }>("/client/bikes")
      .then((r) => setBikes(r.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    reload();
  }, []);

  const filtered = useMemo(() => {
    let list = bikes;
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      list = list.filter(
        (b) =>
          b.model.toLowerCase().includes(q) ||
          b.plate_number.toLowerCase().includes(q)
      );
    }
    if (priceFrom > 0) {
      list = list.filter((b) => Number(b.daily_price) >= priceFrom);
    }
    if (license !== "any") {
      list = list.filter((b) => {
        const req = (b.engine_cc ?? 0) > 50;
        return license === "yes" ? req : !req;
      });
    }
    if (ccFilter !== null) {
      list = list.filter((b) => b.engine_cc === ccFilter);
    }
    return list;
  }, [bikes, query, priceFrom, license, ccFilter]);

  const activeFiltersCount =
    (license !== "any" ? 1 : 0) +
    (ccFilter !== null ? 1 : 0) +
    (priceFrom > 0 ? 1 : 0);

  return (
    <div className="page">
      <h1 className="page-title">Каталог</h1>

      <div className="row" style={{ marginBottom: 12 }}>
        <input
          className="input"
          placeholder="Поиск по модели или номеру"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ flex: 1 }}
        />
        <button
          className={`chip ${activeFiltersCount > 0 ? "active" : ""}`}
          onClick={() => setFiltersOpen(true)}
        >
          Фильтры{activeFiltersCount > 0 ? ` ${activeFiltersCount}` : ""}
        </button>
      </div>

      {loading && <div className="empty">Загрузка</div>}
      {error && (
        <div className="empty" style={{ color: "var(--danger)" }}>
          {error}
        </div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <div className="empty">
          {bikes.length === 0
            ? "В этом парке пока нет байков"
            : "Ничего не найдено, сбросьте фильтры"}
        </div>
      )}

      <div className="bike-grid">
        {filtered.map((bike) => (
          <BikeCard
            key={bike.id}
            bike={bike}
            onClick={(e) => { e.stopPropagation(); setTimeout(() => setSelectedBike(bike), 0); }}
          />
        ))}
      </div>

      {filtersOpen && (
        <FiltersSheet
          onClose={() => setFiltersOpen(false)}
          priceFrom={priceFrom}
          setPriceFrom={setPriceFrom}
          license={license}
          setLicense={setLicense}
          ccFilter={ccFilter}
          setCcFilter={setCcFilter}
          onReset={() => {
            setPriceFrom(0);
            setLicense("any");
            setCcFilter(null);
          }}
        />
      )}

      {selectedBike && (
        <BikeDetailsModal
          bike={selectedBike}
          onClose={() => setSelectedBike(null)}
          onCreated={() => {
            setSelectedBike(null);
            reload();
          }}
        />
      )}
    </div>
  );
}

function BikeCard({ bike, onClick }: { bike: BikeItem; onClick: (e: React.MouseEvent) => void }) {
  const status = bike.status as Status;
  const licenseRequired = (bike.engine_cc ?? 0) > 50;
  const photo = bike.photos[0];

  return (
    <div className="bike-card" onClick={(e) => onClick(e)}>
      {photo ? (
        <img
          className="bike-card-image"
          src={photo}
          alt={bike.model}
          loading="lazy"
        />
      ) : (
        <div className="bike-card-image-empty">Байк</div>
      )}
      <div className="bike-card-body">
        <h3 className="bike-card-title">{bike.model}</h3>
        <div className="bike-card-meta">
          <span className={`badge ${STATUS_CLASS[status]}`}>
            {STATUS_LABEL[status]}
          </span>
          {bike.engine_cc !== null && <span>{bike.engine_cc} cc</span>}
        </div>
        <div className="bike-card-meta">
          <span className="bike-card-price">
            {formatMoney(bike.daily_price)} <span>/день</span>
          </span>
        </div>
        <span
          className={`badge ${
            licenseRequired ? "badge-license" : "badge-nolicense"
          }`}
          style={{ fontSize: 11 }}
        >
          {licenseRequired ? "Права нужны" : "Без прав"}
        </span>
      </div>
    </div>
  );
}

interface FiltersSheetProps {
  onClose: () => void;
  priceFrom: number;
  setPriceFrom: (v: number) => void;
  license: "any" | "yes" | "no";
  setLicense: (v: "any" | "yes" | "no") => void;
  ccFilter: number | null;
  setCcFilter: (v: number | null) => void;
  onReset: () => void;
}

function FiltersSheet(p: FiltersSheetProps) {
  const [priceInput, setPriceInput] = useState<string>(
    p.priceFrom === 0 ? "" : String(p.priceFrom)
  );

  useEffect(() => {
    setPriceInput(p.priceFrom === 0 ? "" : String(p.priceFrom));
  }, [p.priceFrom]);

  return (
    <div className="sheet-backdrop" onClick={p.onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-handle" />

        <div
          className="row"
          style={{ justifyContent: "space-between", marginBottom: 16 }}
        >
          <h2 style={{ margin: 0, fontSize: 20 }}>Фильтры</h2>
          <button className="btn-ghost" onClick={p.onReset}>
            Сбросить
          </button>
        </div>

        <label className="label">Цена от: {formatMoney(p.priceFrom)}</label>
        <input
          className="input price-input"
          type="number"
          inputMode="numeric"
          min={0}
          max={PRICE_MAX}
          step={10000}
          placeholder="0"
          value={priceInput}
          onChange={(e) => {
            const raw = e.target.value.replace(/[^0-9]/g, "");
            if (raw === "") {
              setPriceInput("");
              p.setPriceFrom(0);
              return;
            }
            const n = Math.min(Number(raw), PRICE_MAX);
            setPriceInput(String(n));
            p.setPriceFrom(n);
          }}
          style={{ marginBottom: 12 }}
        />
        <input
          type="range"
          min={0}
          max={PRICE_MAX}
          step={10000}
          value={p.priceFrom}
          onChange={(e) => p.setPriceFrom(Number(e.target.value))}
          style={{ width: "100%", marginBottom: 24 }}
        />

        <label className="label">Права</label>
        <div className="option-list" style={{ marginBottom: 24 }}>
          <OptionRadio
            name="license"
            label="Любые"
            checked={p.license === "any"}
            onChange={() => p.setLicense("any")}
          />
          <OptionRadio
            name="license"
            label="Права нужны"
            checked={p.license === "yes"}
            onChange={() => p.setLicense("yes")}
          />
          <OptionRadio
            name="license"
            label="Без прав"
            checked={p.license === "no"}
            onChange={() => p.setLicense("no")}
          />
        </div>

        <label className="label">Сколько кубов хотите?</label>
        <div className="option-list" style={{ marginBottom: 24 }}>
          <OptionRadio
            name="cc"
            label="Любой объём"
            checked={p.ccFilter === null}
            onChange={() => p.setCcFilter(null)}
          />
          {CC_OPTIONS.map((cc) => (
            <OptionRadio
              key={cc}
              name="cc"
              label={`${cc} cc`}
              checked={p.ccFilter === cc}
              onChange={() => p.setCcFilter(cc)}
            />
          ))}
        </div>

        <button
          className="btn"
          onClick={p.onClose}
          style={{ width: "100%", marginTop: 8 }}
        >
          Показать
        </button>
      </div>
    </div>
  );
}

function OptionRadio({
  name,
  label,
  checked,
  onChange,
}: {
  name: string;
  label: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label
      className={`option-radio ${checked ? "checked" : ""}`}
      htmlFor={`${name}-${label}`}
    >
      <input
        id={`${name}-${label}`}
        type="radio"
        name={name}
        checked={checked}
        onChange={onChange}
        style={{ display: "none" }}
      />
      <span className="option-radio-dot" aria-hidden="true">
        {checked && <span className="option-radio-dot-inner" />}
      </span>
      <span className="option-radio-label">{label}</span>
    </label>
  );
}

function formatMoney(v: string | number): string {
  const n = Number(v);
  if (isNaN(n)) return "0 VND";
  return n.toLocaleString("ru-RU") + " VND";
}
