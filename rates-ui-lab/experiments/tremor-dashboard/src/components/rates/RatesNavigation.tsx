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
  RiLineChartLine,
  RiMenuLine,
} from "@remixicon/react"
import Link from "next/link"

function NavigationLinks({ mobile = false }: { mobile?: boolean }) {
  const links = [
    {
      label: "JGB Rates Analytics",
      href: "/rates",
      icon: RiLineChartLine,
      active: true,
    },
    {
      label: "21st.dev sample",
      href: "/rates-21st",
      icon: RiLineChartLine,
      active: false,
    },
    {
      label: "元の Dashboard",
      href: "/overview",
      icon: RiArrowLeftLine,
      active: false,
    },
  ]
  return (
    <ul className="space-y-1">
      {links.map((link) => {
        const element = (
          <Link
            href={link.href}
            className={cx(
              "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium hover:bg-gray-100 dark:hover:bg-gray-900",
              focusRing,
              link.active
                ? "text-indigo-600 dark:text-indigo-400"
                : "text-gray-600 dark:text-gray-400",
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

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex size-9 items-center justify-center rounded-md bg-indigo-600 text-white">
        <RiLineChartLine className="size-5" aria-hidden="true" />
      </div>
      <div>
        <p className="text-sm font-semibold text-gray-900 dark:text-gray-50">
          Rates UI Lab
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400">01 · Tremor</p>
      </div>
    </div>
  )
}

export function RatesNavigation() {
  return (
    <>
      <nav
        aria-label="実験ナビゲーション"
        className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-72 lg:flex-col"
      >
        <div className="flex h-full flex-col border-r border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-950">
          <div className="px-2 py-1">
            <Brand />
          </div>
          <div className="mt-9">
            <NavigationLinks />
          </div>
          <div className="mt-10 px-3">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
              参照したテンプレート
            </p>
            <a
              href="https://blocks.tremor.so/blocks/kpi-cards"
              target="_blank"
              rel="noreferrer"
              className={cx(
                "mt-3 flex items-center justify-between rounded text-sm text-gray-600 hover:text-indigo-600 dark:text-gray-400 dark:hover:text-indigo-400",
                focusRing,
              )}
            >
              Tremor Blocks
              <RiArrowRightUpLine className="size-4" aria-hidden="true" />
            </a>
          </div>
          <div className="mt-auto border-t border-gray-200 px-3 pt-4 dark:border-gray-800">
            <p className="text-xs font-medium text-gray-900 dark:text-gray-50">
              JPY / 日本国債
            </p>
            <p className="mt-1 text-xs leading-5 text-gray-500 dark:text-gray-400">
              固定の仮データで UI を比較。
              <br />
              値は実勢金利ではありません。
            </p>
          </div>
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
              <DrawerTitle>Rates UI Lab</DrawerTitle>
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
