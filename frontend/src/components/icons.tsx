// SVG-иконки 20×20 для таб-бара и интерфейса.
// Стиль — stroke, как в новой UI (.ic).
export function IconCatalog() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-6 9 6v11a2 2 0 0 1-2 2h-4v-7h-6v7H5a2 2 0 0 1-2-2z" />
    </svg>
  );
}

export function IconHistory() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 1 0 3-6.7" />
      <path d="M3 4v5h5" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

export function IconGarage() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 21V8l9-5 9 5v13" />
      <path d="M9 21v-6h6v6" />
    </svg>
  );
}

export function IconExpenses() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="6" width="18" height="13" rx="2" />
      <path d="M3 10h18" />
      <path d="M7 15h4" />
    </svg>
  );
}

export function IconRequests() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M10 21a2 2 0 0 0 4 0" />
    </svg>
  );
}

export function IconAnalytics() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <path d="M7 15l4-4 3 3 5-5" />
    </svg>
  );
}

export function IconProfile() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
    </svg>
  );
}

export function IconSummary() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="9" rx="1" />
      <rect x="14" y="3" width="7" height="5" rx="1" />
      <rect x="14" y="12" width="7" height="9" rx="1" />
      <rect x="3" y="16" width="7" height="5" rx="1" />
    </svg>
  );
}

export function IconParks() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 21h18" />
      <path d="M5 21V7l7-4 7 4v14" />
      <path d="M9 21v-4h6v4" />
      <path d="M9 11h.01M15 11h.01" />
    </svg>
  );
}

export function IconPayments() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="6" width="20" height="13" rx="2" />
      <path d="M2 10h20" />
      <path d="M7 15h4" />
    </svg>
  );
}
