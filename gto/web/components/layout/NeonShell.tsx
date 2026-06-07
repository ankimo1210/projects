"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";

const NAV = [
  { href: "/neon",    label: "TRAINER" },
  { href: "/library", label: "LIBRARY" },
  { href: "/report",  label: "REPORT"  },
  { href: "/solver",     label: "SOLVER"   },
  { href: "/simulation", label: "SIMULATE" },
  { href: "/review",     label: "REVIEW"   },
];

interface NeonShellProps {
  /** Right-side header slot (e.g. session stats, position selector) */
  rightSlot?: ReactNode;
  children: ReactNode;
}

export default function NeonShell({ rightSlot, children }: NeonShellProps) {
  const path = usePathname();

  return (
    <div className="min-h-screen bg-[#070710] text-white font-mono overflow-hidden">
      {/* Scanline overlay */}
      <div
        className="pointer-events-none fixed inset-0 z-50"
        style={{
          background:
            "repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.025) 2px,rgba(0,0,0,0.025) 4px)",
        }}
      />

      {/* Header */}
      <header
        className="border-b border-cyan-500/20 px-4 py-2 flex items-center gap-4"
        style={{ boxShadow: "0 1px 0 rgba(34,211,238,0.1)" }}
      >
        {/* Logo */}
        <Link
          href="/"
          className="text-cyan-500/50 text-xs tracking-widest hover:text-cyan-400 transition-colors shrink-0"
        >
          GTO://
        </Link>

        {/* Nav tabs */}
        <nav className="flex items-center gap-1">
          {NAV.map(({ href, label }) => {
            const active = path === href || path.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                className={`px-3 py-1 text-xs tracking-widest border transition-all rounded-sm
                  ${active
                    ? "border-cyan-400/60 text-cyan-300 bg-cyan-400/10"
                    : "border-transparent text-zinc-600 hover:text-zinc-400 hover:border-zinc-700"
                  }`}
                style={active ? { textShadow: "0 0 8px rgba(34,211,238,0.6)" } : undefined}
              >
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Right slot */}
        {rightSlot && (
          <div className="ml-auto flex items-center gap-4 text-xs">
            {rightSlot}
          </div>
        )}
      </header>

      {/* Page content */}
      <div className="h-[calc(100vh-41px)] overflow-auto">
        {children}
      </div>
    </div>
  );
}
