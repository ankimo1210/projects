"use client"

import { Button } from "@/components/Button"
import {
  Drawer,
  DrawerBody,
  DrawerClose,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/Drawer"
import { cx, focusRing } from "@/lib/utils"
import {
  RiArrowLeftLine,
  RiArrowRightUpLine,
  RiDatabase2Line,
  RiDashboard3Line,
  RiMenuLine,
} from "@remixicon/react"
import Link from "next/link"

const links = [
  {
    label: "Meshyflix study",
    href: "/rates-21st?view=meshy",
    icon: RiDashboard3Line,
  },
  {
    label: "Prism Hero",
    href: "/rates-21st?view=prism",
    icon: RiDashboard3Line,
  },
  {
    label: "Market overview",
    href: "/rates-21st",
    icon: RiDashboard3Line,
  },
  {
    label: "Massive data lab",
    href: "/rates-21st?view=massive&rows=100000",
    icon: RiDatabase2Line,
  },
  {
    label: "Tremor comparison",
    href: "/rates?layout=blocks",
    icon: RiArrowLeftLine,
  },
] as const

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex size-10 items-center justify-center rounded-2xl bg-gray-950 text-sm font-black text-white ring-1 ring-white/10 dark:bg-white dark:text-gray-950">
        21
      </div>
      <div>
        <p className="text-sm font-semibold text-gray-950 dark:text-white">
          Rates UI Lab
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          02 · UI + 3D studies
        </p>
      </div>
    </div>
  )
}

function NavigationLinks({ mobile = false }: { mobile?: boolean }) {
  return (
    <ul className="space-y-1.5">
      {links.map((link) => {
        const element = (
          <Link
            href={link.href}
            className={cx(
              "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
              focusRing,
              "text-gray-600 hover:bg-gray-100 hover:text-gray-950 dark:text-gray-400 dark:hover:bg-gray-900 dark:hover:text-white",
            )}
          >
            <link.icon className="size-4" aria-hidden="true" />
            {link.label}
          </Link>
        )
        return (
          <li key={link.href}>
            {mobile ? <DrawerClose asChild>{element}</DrawerClose> : element}
          </li>
        )
      })}
    </ul>
  )
}

export function TwentyFirstNavigation() {
  return (
    <>
      <nav
        aria-label="21st.dev 実験ナビゲーション"
        className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-72 lg:flex-col"
      >
        <div className="m-3 flex h-[calc(100%-1.5rem)] flex-col rounded-3xl border border-gray-200 bg-gray-50 p-4 shadow-sm dark:border-gray-800 dark:bg-gray-950">
          <div className="px-2 py-2">
            <Brand />
          </div>
          <div className="mt-8">
            <NavigationLinks />
          </div>
          <div className="mt-8 rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
              Reference
            </p>
            <div className="mt-3 space-y-2">
              <a
                href="https://21st.dev/@uilayout.contact/components/stats-bento"
                target="_blank"
                rel="noreferrer"
                className={cx(
                  "flex items-center justify-between text-sm font-medium text-gray-900 hover:text-indigo-600 dark:text-gray-100 dark:hover:text-indigo-400",
                  focusRing,
                )}
              >
                Stats Bento
                <RiArrowRightUpLine className="size-4" aria-hidden="true" />
              </a>
              <a
                href="https://21st.dev/@bevelui/components/prism-hero"
                target="_blank"
                rel="noreferrer"
                className={cx(
                  "flex items-center justify-between text-sm font-medium text-gray-900 hover:text-indigo-600 dark:text-gray-100 dark:hover:text-indigo-400",
                  focusRing,
                )}
              >
                Prism Hero
                <RiArrowRightUpLine className="size-4" aria-hidden="true" />
              </a>
            </div>
            <p className="mt-2 text-xs leading-5 text-gray-500 dark:text-gray-400">
              21st.dev patterns · MIT
              <br />
              Data and chart logic are local.
            </p>
            <a
              href="https://meshyflix.com/"
              target="_blank"
              rel="noreferrer"
              className={cx("mt-4 flex items-center justify-between border-t border-gray-200 pt-3 text-sm font-medium text-gray-900 hover:text-indigo-600 dark:border-gray-800 dark:text-gray-100 dark:hover:text-indigo-400", focusRing)}
            >
              Meshyflix website
              <RiArrowRightUpLine className="size-4" aria-hidden="true" />
            </a>
          </div>
          <p className="mt-auto px-3 pb-2 text-xs leading-5 text-gray-500 dark:text-gray-400">
            100万行はブラウザ内で生成。
            <br />
            実勢金利ではありません。
          </p>
        </div>
      </nav>
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 lg:hidden dark:border-gray-800 dark:bg-gray-950">
        <Brand />
        <Drawer>
          <DrawerTrigger asChild>
            <Button variant="ghost" aria-label="ナビゲーションを開く">
              <RiMenuLine className="size-5" />
            </Button>
          </DrawerTrigger>
          <DrawerContent>
            <DrawerHeader>
              <DrawerTitle>UI + 3D studies</DrawerTitle>
            </DrawerHeader>
            <DrawerBody>
              <NavigationLinks mobile />
            </DrawerBody>
          </DrawerContent>
        </Drawer>
      </div>
    </>
  )
}
