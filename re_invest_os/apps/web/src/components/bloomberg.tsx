/**
 * Bloomberg基調の共通UIコンポーネント。
 * デザイン原則: docs/design/design_principles.md
 * トークン: src/app/globals.css (--bg, --accent, --good, --bad など)
 */
import type { ReactNode } from "react";

// ===== Layout primitives =====

export function Panel({
  className,
  title,
  meta,
  children,
}: {
  className?: string;
  title: string;
  meta?: string;
  children: ReactNode;
}) {
  return (
    <section
      className={`bg-[var(--surface)] border border-[var(--border)] ${className ?? ""}`}
    >
      <header className="flex items-center justify-between bg-[var(--surface-alt)] border-b border-[var(--border)] px-3 py-1.5">
        <span className="text-[var(--accent)] font-mono font-bold text-[10px] tracking-widest uppercase">
          {title}
        </span>
        {meta && (
          <span className="text-[var(--text-subtle)] font-mono text-[9px]">{meta}</span>
        )}
      </header>
      <div>{children}</div>
    </section>
  );
}

// ===== Navigation =====

export function CmdKey({
  label,
  name,
  href,
  active,
}: {
  label: string;
  name: string;
  href?: string;
  active?: boolean;
}) {
  const content = (
    <>
      <span className="bg-[var(--accent)] text-[var(--bg)] px-1.5 py-0.5 font-mono font-bold text-[10px]">
        {label}
      </span>
      <span
        className={`px-2 py-0.5 font-mono text-[11px] ${
          active ? "text-[var(--text)]" : "text-[var(--text-muted)]"
        }`}
      >
        {name}
      </span>
    </>
  );
  if (href) {
    return (
      <a
        href={href}
        className="flex hover:opacity-80 transition-opacity"
        aria-current={active ? "page" : undefined}
      >
        {content}
      </a>
    );
  }
  return <div className="flex">{content}</div>;
}

export function Tick({
  label,
  value,
  delta,
  good,
  bad,
}: {
  label: string;
  value: string;
  delta?: string;
  good?: boolean;
  bad?: boolean;
}) {
  return (
    <span>
      <strong className="text-[var(--accent)] mr-1">{label}</strong>
      {value}
      {delta && (
        <span
          className={`ml-1 ${good ? "text-[var(--good)]" : bad ? "text-[var(--bad)]" : ""}`}
        >
          {delta}
        </span>
      )}
    </span>
  );
}

// ===== Data rows =====

type Severity = "good" | "bad" | "warn" | undefined;

function severityClass(s: Severity) {
  return s === "good"
    ? "text-[var(--good)]"
    : s === "bad"
      ? "text-[var(--bad)]"
      : s === "warn"
        ? "text-[var(--warn)]"
        : "";
}

export function Row({
  label,
  value,
  severity,
  good,
  bad,
  warn,
}: {
  label: string;
  value: string;
  severity?: Severity;
  good?: boolean;
  bad?: boolean;
  warn?: boolean;
}) {
  const sev: Severity = severity ?? (good ? "good" : bad ? "bad" : warn ? "warn" : undefined);
  return (
    <div className="flex justify-between gap-2 py-0.5">
      <span className="text-[var(--text-muted)] w-32">{label}</span>
      <span className={`font-mono tabular-nums ${severityClass(sev)}`}>{value}</span>
    </div>
  );
}

export function KpiCell({
  name,
  value,
  note,
  severity,
  good,
  bad,
  warn,
}: {
  name: string;
  value: string;
  note?: string;
  severity?: Severity;
  good?: boolean;
  bad?: boolean;
  warn?: boolean;
}) {
  const sev: Severity = severity ?? (good ? "good" : bad ? "bad" : warn ? "warn" : undefined);
  const color =
    sev === "good"
      ? "var(--good)"
      : sev === "bad"
        ? "var(--bad)"
        : sev === "warn"
          ? "var(--warn)"
          : "var(--text)";
  return (
    <div className="bg-[var(--surface)] px-3 py-2.5">
      <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-widest font-mono mb-1">
        {name}
      </div>
      <div
        className="text-[22px] font-mono font-bold tabular-nums leading-none"
        style={{ color }}
      >
        {value}
      </div>
      {note && (
        <div
          className="text-[9px] mt-1 font-mono"
          style={{ color: sev === "bad" ? "var(--bad)" : "var(--text-muted)" }}
        >
          {note}
        </div>
      )}
    </div>
  );
}

// ===== Badges =====

export function Badge({
  level,
  children,
}: {
  level: "good" | "warn" | "bad";
  children: ReactNode;
}) {
  const bg =
    level === "good" ? "var(--good)" : level === "warn" ? "var(--warn)" : "var(--bad)";
  const fg = level === "bad" ? "white" : "var(--bg)";
  return (
    <span
      className="inline-block px-1.5 py-px font-mono font-bold text-[9px] uppercase tracking-widest"
      style={{ background: bg, color: fg }}
    >
      {children}
    </span>
  );
}

// ===== Buttons =====

export function Btn({
  variant = "primary",
  type = "button",
  disabled,
  children,
  onClick,
  className,
}: {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  type?: "button" | "submit" | "reset";
  disabled?: boolean;
  children: ReactNode;
  onClick?: () => void;
  className?: string;
}) {
  const styles: Record<string, string> = {
    primary:
      "bg-[var(--accent)] text-[var(--bg)] hover:opacity-90 border border-[var(--accent)]",
    secondary:
      "bg-transparent text-[var(--accent)] border border-[var(--accent)] hover:bg-[var(--accent)] hover:text-[var(--bg)]",
    danger:
      "bg-[var(--bad)] text-white border border-[var(--bad)] hover:opacity-90",
    ghost:
      "bg-transparent text-[var(--text)] border border-[var(--border)] hover:bg-[var(--surface-alt)]",
  };
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`px-3 py-1.5 text-[11px] font-mono font-bold uppercase tracking-widest transition-opacity disabled:opacity-40 disabled:cursor-not-allowed ${styles[variant]} ${className ?? ""}`}
    >
      {children}
    </button>
  );
}

// ===== Inputs =====

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] font-mono uppercase tracking-widest text-[var(--text-muted)]">
        {label}
      </span>
      {children}
      {hint && <span className="text-[9px] text-[var(--text-subtle)]">{hint}</span>}
    </label>
  );
}

export function Input({
  type = "text",
  value,
  onChange,
  step,
  min,
  max,
  placeholder,
  required,
  className,
}: {
  type?: "text" | "number";
  value: string | number;
  onChange: (v: string) => void;
  step?: string;
  min?: number;
  max?: number;
  placeholder?: string;
  required?: boolean;
  className?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      step={step}
      min={min}
      max={max}
      placeholder={placeholder}
      required={required}
      className={`bg-[var(--bg)] border border-[var(--border)] focus:border-[var(--accent)] focus:outline-none px-2 py-1 font-mono text-[12px] tabular-nums text-right ${className ?? ""}`}
    />
  );
}

export function Select<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: ReadonlyArray<{ value: T; label: string }>;
  onChange: (v: T) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as T)}
      className="bg-[var(--bg)] border border-[var(--border)] focus:border-[var(--accent)] focus:outline-none px-2 py-1 font-mono text-[12px]"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

// ===== Formatters =====

export const fmtYen = (n: number) => `¥${n.toLocaleString("en-US")}`;
export const fmtPct = (n: number, d = 2) => `${(n * 100).toFixed(d)}%`;
export const fmtSignedPct = (n: number, d = 2) => `${n >= 0 ? "+" : ""}${(n * 100).toFixed(d)}%`;
