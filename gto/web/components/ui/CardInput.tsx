"use client";

import { ChangeEvent } from "react";

interface CardInputProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}

export function CardInput({ label, value, onChange, placeholder }: CardInputProps) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs text-zinc-400 uppercase tracking-wider">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
        placeholder={placeholder ?? "e.g. Ah Kh"}
        className="bg-zinc-800 border border-zinc-600 text-white rounded px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-sky-500 w-40"
      />
    </div>
  );
}
