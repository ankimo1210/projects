import { test, expect } from "@playwright/test"

test("金利画面が同じデータから指標・カーブ・表を表示する", async ({ page }) => {
  await page.goto("/rates?layout=template")
  await expect(
    page.getByRole("heading", { name: "JGB Rates Analytics" }),
  ).toBeVisible()
  await expect(
    page.getByTestId("kpi-tenY").getByTestId("kpi-value"),
  ).toHaveText("1.850%")
  await expect(
    page.getByTestId("kpi-twoTen").getByTestId("kpi-value"),
  ).toHaveText("+93.0 bp")
  await expect(
    page.getByTestId("kpi-fiveThirty").getByTestId("kpi-value"),
  ).toHaveText("+123.0 bp")
  await expect(page.getByTestId("tenor-row-10")).toContainText("1.850%")
  await expect(page.getByTestId("yield-curve")).toBeVisible()
  await expect(page.getByTestId("curve-move")).toBeVisible()
  const xs = await page
    .getByTestId("yield-curve")
    .locator(".recharts-line")
    .nth(1)
    .locator(".recharts-dot")
    .evaluateAll((dots) => dots.map((dot) => Number(dot.getAttribute("cx"))))
  expect(xs).toHaveLength(7)
  expect((xs[4] - xs[3]) / (xs[1] - xs[0])).toBeCloseTo(10 / 3, 3)
})

async function pick(
  page: import("@playwright/test").Page,
  name: string,
  value: string,
) {
  await page.getByRole("combobox", { name, exact: true }).click()
  await page.getByRole("option", { name: value, exact: true }).click()
}

test("日付・凡例・選択年限・表ソートを保ったまま Blocks に切り替わる", async ({
  page,
}) => {
  await page.goto("/rates?layout=template")
  await pick(page, "基準日", "2026-08-31")
  await pick(page, "比較日", "2026-08-24")
  await page.getByRole("button", { name: "10Yを強調", exact: true }).click()
  await page.getByRole("button", { name: "利回り", exact: true }).click()
  await page
    .getByRole("button", { name: "比較日のカーブ", exact: true })
    .click()
  const kpis = await page.getByTestId("kpi-value").allTextContents()
  const domain = await page
    .getByTestId("yield-curve")
    .getAttribute("data-domain")
  await page.getByRole("button", { name: /^Blocks/ }).click()
  await expect(page).toHaveURL(/layout=blocks/)
  await expect(page.getByTestId("as-of")).toHaveText(
    "基準日 2026-08-31 · 比較日 2026-08-24",
  )
  await expect(page.getByTestId("kpi-value")).toHaveText(kpis)
  await expect(page.getByTestId("yield-curve")).toHaveAttribute(
    "data-domain",
    domain!,
  )
  await expect(
    page.getByRole("button", { name: "10Yを強調", exact: true }),
  ).toHaveAttribute("aria-pressed", "true")
  await expect(
    page.getByRole("button", { name: "比較日のカーブ", exact: true }),
  ).toHaveAttribute("aria-pressed", "false")
  await expect(page.locator("tbody tr").first()).toHaveAttribute(
    "data-testid",
    "tenor-row-40",
  )
  await expect(page.getByRole("img", { name: /観測日の推移/ })).toHaveCount(4)
  await page.getByRole("button", { name: "20営業日前", exact: true }).click()
  await expect(page.getByTestId("as-of")).toContainText("比較日 2026-08-03")
  await page
    .getByRole("button", { name: "最新の観測日に戻す", exact: true })
    .click()
  await expect(page.getByTestId("as-of")).toHaveText(
    "基準日 2026-09-04 · 比較日 2026-09-03",
  )
  await page.getByRole("button", { name: "5営業日前", exact: true }).click()
  await expect(page.getByTestId("as-of")).toContainText("比較日 2026-08-28")
})

test("欠損をゼロ埋めせずカーブを分断し、負金利とゼロスプレッドも表示する", async ({
  page,
}) => {
  await page.goto("/rates?layout=blocks")
  await pick(page, "仮データのケース", "欠損のあるカーブ")
  await expect(
    page.getByTestId("kpi-tenY").getByTestId("kpi-value"),
  ).toHaveText("—")
  await expect(
    page.getByTestId("kpi-twoTen").getByTestId("kpi-value"),
  ).toHaveText("—")
  await expect(
    page.getByTestId("tenor-row-10").locator("td").first(),
  ).toHaveText("—")
  const currentPath = await page
    .getByTestId("yield-curve")
    .locator(".recharts-line")
    .nth(1)
    .locator(".recharts-line-curve")
    .getAttribute("d")
  expect((currentPath?.match(/M/g) || []).length).toBeGreaterThan(1)
  await pick(page, "仮データのケース", "負金利のカーブ")
  await expect(
    page.getByTestId("tenor-row-2").locator("td").first(),
  ).toHaveText(/^-\d/)
  const domain = (await page
    .getByTestId("yield-curve")
    .getAttribute("data-domain"))!
    .split(",")
    .map(Number)
  expect(domain[0]).toBeLessThan(0)
  await pick(page, "仮データのケース", "フラットなカーブ")
  await expect(
    page.getByTestId("kpi-twoTen").getByTestId("kpi-value"),
  ).toHaveText("0.0 bp")
  await expect(
    page.getByTestId("kpi-fiveThirty").getByTestId("kpi-value"),
  ).toHaveText("0.0 bp")
  const values = await page
    .locator("tbody tr td:first-of-type")
    .allTextContents()
  expect(new Set(values).size).toBe(1)
  await expect(page.locator("main")).not.toContainText("NaN")
})

test("キーボードで日付・レイアウト・テーマを操作でき、最初の観測日は差分が欠損になる", async ({
  page,
}) => {
  await page.goto("/rates?layout=blocks")
  const date = page.getByRole("combobox", { name: "基準日", exact: true })
  await date.focus()
  await page.keyboard.press("Enter")
  await expect(page.getByRole("listbox")).toBeVisible()
  await expect(
    page.getByRole("option", { name: "2026-09-04", exact: true }),
  ).toBeFocused()
  await page.keyboard.press("End")
  await expect(
    page.getByRole("option", { name: "2026-06-15", exact: true }),
  ).toBeFocused()
  await page.keyboard.press("Enter")
  await expect(page.getByTestId("as-of")).toContainText("基準日 2026-06-15")
  await expect(page.getByTestId("kpi-day")).toHaveText(["—", "—", "—", "—"])
  await expect(
    page.getByRole("button", { name: "5営業日前", exact: true }),
  ).toBeDisabled()
  const template = page.getByRole("button", { name: /^Template/ })
  await template.focus()
  await expect(template).toBeFocused()
  await page.keyboard.press("Enter")
  await expect(template).toHaveAttribute("aria-pressed", "true")
  const themeButton = page.getByRole("button", {
    name: "ダークモードに切り替え",
    exact: true,
  })
  await themeButton.focus()
  await page.keyboard.press("Enter")
  await expect(page.locator("html")).toHaveClass(/dark/)
  await page.reload()
  await expect(page.locator("html")).toHaveClass(/dark/)
})

for (const theme of ["light", "dark"] as const) {
  for (const width of [1440, 1280, 390]) {
    for (const layout of ["template", "blocks"]) {
      test(`${layout} / ${theme} / ${width}px に横溢れ・カードの文字溢れ・実行時エラーがない`, async ({
        page,
      }) => {
        await page.setViewportSize({ width, height: 1000 })
        await page.addInitScript(
          (value) => localStorage.setItem("theme", value),
          theme,
        )
        const errors: string[] = []
        page.on("pageerror", (error) => errors.push(error.message))
        page.on("console", (message) => {
          if (message.type() === "error") errors.push(message.text())
        })
        await page.goto(`/rates?layout=${layout}`)
        await expect(page.getByTestId("kpi-tenY")).toBeVisible()
        await page.waitForLoadState("networkidle")
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth > innerWidth,
          ),
        ).toBe(false)
        const spills = await page
          .getByTestId("kpi-value")
          .evaluateAll(
            (elements) =>
              elements.filter(
                (element) => element.scrollWidth > element.clientWidth,
              ).length,
          )
        expect(spills).toBe(0)
        for (const name of ["基準日", "比較日"]) {
          const bounds = await page
            .getByRole("combobox", { name, exact: true })
            .boundingBox()
          expect(bounds!.width).toBeGreaterThanOrEqual(150)
        }
        expect(errors).toEqual([])
        await page.screenshot({
          path: `../../docs/screenshots/${layout}-${theme}-${width}.png`,
          fullPage: true,
        })
        if (width === 390) {
          await page
            .getByRole("button", { name: "ナビゲーションを開く" })
            .click()
          await expect(
            page.getByRole("link", { name: "元の Dashboard", exact: true }),
          ).toBeVisible()
        }
      })
    }
  }
}

test("不正なデータケース名を指定しても標準の金利画面へ戻る", async ({
  page,
}) => {
  for (const value of ["__proto__", "constructor", "unknown"]) {
    await page.goto(`/rates?case=${value}`)
    await expect(
      page.getByTestId("kpi-tenY").getByTestId("kpi-value"),
    ).toHaveText("1.850%")
  }
})

test("欠損年限のツールチップにも — を表示する", async ({ page }) => {
  await page.goto("/rates?layout=blocks&case=missing")
  const chart = page.getByTestId("curve-move")
  const tick = chart
    .locator(".recharts-xAxis .recharts-cartesian-axis-tick")
    .filter({ hasText: "10Y" })
  const tickBox = (await tick.boundingBox())!
  const chartBox = (await chart.boundingBox())!
  await page.mouse.move(
    tickBox.x + tickBox.width / 2,
    chartBox.y + chartBox.height / 2,
  )
  await expect(chart.locator(".recharts-tooltip-wrapper")).toBeVisible()
  await expect(chart.locator(".recharts-tooltip-wrapper")).toContainText("—")
})

test("21st.dev sample は同じ金利指標を bento layout で表示する", async ({
  page,
}) => {
  await page.goto("/rates-21st")
  await expect(
    page.getByRole("heading", { name: "JGB Market Pulse" }),
  ).toBeVisible()
  await expect(page.getByTestId("twentyfirst-kpi-tenY")).toContainText("1.850%")
  await expect(page.getByTestId("twentyfirst-kpi-twoTen")).toContainText(
    "+93.0 bp",
  )
  await expect(page.getByTestId("twentyfirst-yield-curve")).toBeVisible()
  const invertedCard = page.locator("section").filter({ hasText: "5s30s" }).first()
  const invertedColors = await invertedCard.evaluate((element) => {
    const style = getComputedStyle(element)
    return { background: style.backgroundColor, foreground: style.color }
  })
  expect(invertedColors.background).not.toBe(invertedColors.foreground)
  const yTicks = await page
    .getByTestId("twentyfirst-yield-curve")
    .locator(".recharts-yAxis .recharts-cartesian-axis-tick-value")
    .allTextContents()
  expect(yTicks).not.toEqual([])
  expect(yTicks.every((tick) => /^-?\d+\.\d{2}$/.test(tick))).toBe(true)
  await expect(
    page.getByRole("link", { name: "Stats Bento on 21st.dev" }),
  ).toHaveAttribute(
    "href",
    "https://21st.dev/@uilayout.contact/components/stats-bento",
  )
})

test("massive data lab は100万行をWorkerで生成して表を仮想化する", async ({
  page,
}) => {
  test.setTimeout(45_000)
  await page.goto("/rates-21st?view=massive&rows=1000000")
  await expect(page.getByTestId("stress-status")).toHaveText("1,000,000 rows ready", {
    timeout: 20_000,
  })
  await expect(page.getByTestId("stress-row-count")).toHaveText("1,000,000")
  await expect(page.getByTestId("stress-dom-count")).toHaveText(/\d+/)
  expect(Number(await page.getByTestId("stress-dom-count").textContent())).toBeLessThan(50)
  await expect(
    page.locator('[role="row"][aria-rowindex="1"]'),
  ).toBeVisible()
  const viewportBox = (await page.getByRole("table").boundingBox())!
  const firstRowBox = (
    await page.locator('[role="row"][aria-rowindex="1"]').boundingBox()
  )!
  expect(firstRowBox.y).toBeGreaterThanOrEqual(viewportBox.y)
  expect(firstRowBox.y).toBeLessThan(viewportBox.y + viewportBox.height)

  const initialRange = await page.getByTestId("stress-visible-range").textContent()
  await page.getByRole("button", { name: "50%地点へ移動" }).click()
  await expect(page.getByTestId("stress-visible-range")).not.toHaveText(
    initialRange || "",
  )
  await expect(page.getByTestId("stress-visible-range")).toContainText("500,")
  await expect(
    page.locator('[role="row"][aria-rowindex]').filter({ hasText: "JGB-" }).first(),
  ).toBeVisible()
  await expect(page.getByTestId("stress-table")).toContainText("10Y")
  await expect(page.locator("main")).not.toContainText("NaN")
})

test("Prism Hero はJGBデータとWebGL表現を表示し、reduced motionを尊重する", async ({
  page,
}) => {
  await page.goto("/rates-21st?view=prism")
  await expect(
    page.getByRole("heading", { name: "JGB Refraction" }),
  ).toBeVisible()
  await expect(page.getByTestId("prism-ten-year")).toHaveText("1.850%")
  await expect(page.getByTestId("prism-stage")).toHaveAttribute(
    "data-motion",
    "animated",
  )
  await expect(page.getByTestId("prism-stage").locator("canvas")).toBeVisible()
  await expect(
    page.getByRole("link", { name: "Prism Hero on 21st.dev" }),
  ).toHaveAttribute(
    "href",
    "https://21st.dev/@bevelui/components/prism-hero",
  )

  await page.emulateMedia({ reducedMotion: "reduce" })
  await page.reload()
  await expect(page.getByTestId("prism-stage")).toHaveAttribute(
    "data-motion",
    "static",
  )
})

test("Prism Hero は390pxでCTAと下部メタ情報を重ねない", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto("/rates-21st?view=prism")
  await expect(page.getByTestId("prism-stage").locator("canvas")).toBeVisible()
  await expect(page.getByTestId("prism-mobile-metrics")).toBeVisible()
  await expect(page.getByTestId("prism-bottom-meta")).toBeHidden()
  await expect(page.getByTestId("prism-actions")).toBeVisible()
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),
  ).toBe(false)
})

for (const sample of [
  {
    name: "overview-light-390",
    url: "/rates-21st",
    width: 390,
    theme: "light",
  },
  {
    name: "overview-dark-1440",
    url: "/rates-21st",
    width: 1440,
    theme: "dark",
  },
  {
    name: "massive-dark-390",
    url: "/rates-21st?view=massive&rows=1000000",
    width: 390,
    theme: "dark",
  },
  {
    name: "prism-light-390",
    url: "/rates-21st?view=prism",
    width: 390,
    theme: "light",
  },
] as const) {
  test(`21st.dev ${sample.name} に横溢れ・実行時エラーがない`, async ({
    page,
  }) => {
    test.setTimeout(45_000)
    await page.setViewportSize({ width: sample.width, height: 1000 })
    await page.addInitScript(
      (theme) => localStorage.setItem("theme", theme),
      sample.theme,
    )
    const errors: string[] = []
    page.on("pageerror", (error) => errors.push(error.message))
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text())
    })
    await page.goto(sample.url)
    if (sample.url.includes("view=massive")) {
      await expect(page.getByTestId("stress-status")).toContainText("ready", {
        timeout: 20_000,
      })
    } else if (sample.url.includes("view=prism")) {
      await expect(page.getByTestId("prism-stage").locator("canvas")).toBeVisible()
    } else {
      await expect(page.getByTestId("twentyfirst-yield-curve")).toBeVisible()
    }
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),
    ).toBe(false)
    expect(errors).toEqual([])
    await page.screenshot({
      path: `../../docs/screenshots/21st-${sample.name}.png`,
      fullPage: true,
    })
    if (sample.width === 390) {
      await page
        .getByRole("button", { name: "ナビゲーションを開く" })
        .click()
      await expect(
        page.getByRole("link", { name: "Tremor comparison" }),
      ).toBeVisible()
    }
  })
}
