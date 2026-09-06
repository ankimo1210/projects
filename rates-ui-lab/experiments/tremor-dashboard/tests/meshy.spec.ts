import { expect, test } from "@playwright/test"

test("Meshyflix study switches mesh modes, datasets and downloads the selected observations", async ({ page }) => {
  await page.goto("/rates-21st")
  await page.getByRole("button", { name: "Meshyflix", exact: true }).click()
  await expect(page).toHaveURL(/view=meshy/)
  await expect(page.getByRole("heading", { name: "See the curve. Explore the mesh." })).toBeVisible()
  await expect(page.getByTestId("meshy-canvas").locator("canvas")).toBeVisible()
  await expect(page.getByTestId("meshy-ten-year")).toHaveText("1.850%")
  await expect(page.getByTestId("meshy-vertices")).toHaveText("420")
  await expect(page.getByTestId("meshy-triangles")).toHaveText("708")
  await page.getByRole("button", { name: "Wireframe", exact: true }).click()
  await expect(page.getByRole("button", { name: "Wireframe", exact: true })).toHaveAttribute("aria-pressed", "true")
  await page.getByRole("button", { name: "Points", exact: true }).click()
  await expect(page.getByRole("button", { name: "Points", exact: true })).toHaveAttribute("aria-pressed", "true")
  await page.getByRole("button", { name: "欠損カーブを表示" }).click()
  await expect(page.getByTestId("meshy-ten-year")).toHaveText("—")
  expect(Number(await page.getByTestId("meshy-triangles").textContent())).toBeLessThan(708)
  const downloadPromise = page.waitForEvent("download")
  await page.getByRole("button", { name: "Download CSV", exact: true }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe("jgb-missing-60-observations.csv")
  const stream = (await download.createReadStream())!
  const chunks: Buffer[] = []
  for await (const chunk of stream) chunks.push(Buffer.from(chunk))
  const csv = Buffer.concat(chunks).toString("utf8")
  expect(csv).toContain("2026-09-04,10,\n")
  expect(csv.trimEnd().split("\n")).toHaveLength(421)
  await page.getByRole("button", { name: "負金利カーブを表示" }).click()
  await expect(page.getByTestId("meshy-ten-year")).toHaveText("0.750%")
  await page.getByRole("button", { name: "フラットカーブを表示" }).click()
  await expect(page.getByTestId("meshy-spread")).toHaveText("0.0 bp")
})

test("Meshyflix study supports mobile controls and reduced motion without overflow or runtime errors", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.emulateMedia({ reducedMotion: "reduce" })
  const errors: string[] = []
  page.on("pageerror", error => errors.push(error.message))
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()) })
  await page.goto("/rates-21st?view=meshy")
  await expect(page.getByTestId("meshy-canvas").locator("canvas")).toBeVisible()
  await expect(page.getByRole("button", { name: "自動回転" })).toBeDisabled()
  await page.getByRole("button", { name: "拡大", exact: true }).click()
  await page.getByRole("button", { name: "視点をリセット" }).click()
  await page.getByRole("button", { name: "Wireframe", exact: true }).click()
  await expect(page.getByRole("button", { name: "Wireframe", exact: true })).toHaveAttribute("aria-pressed", "true")
  const tenorBox = (await page.getByTestId("meshy-canvas").getByText("40Y", { exact: true }).boundingBox())!
  const dateBox = (await page.getByTestId("meshy-canvas").getByText("06-15", { exact: true }).boundingBox())!
  const overlaps = tenorBox.x < dateBox.x + dateBox.width && tenorBox.x + tenorBox.width > dateBox.x
    && tenorBox.y < dateBox.y + dateBox.height && tenorBox.y + tenorBox.height > dateBox.y
  expect(overlaps).toBe(false)
  const canvasBox = (await page.getByTestId("meshy-canvas").boundingBox())!
  expect(dateBox.y + dateBox.height).toBeLessThan(canvasBox.y + canvasBox.height)
  expect(tenorBox.y + tenorBox.height).toBeLessThan(canvasBox.y + canvasBox.height)
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
  expect(errors).toEqual([])
  await page.screenshot({ path: "../../docs/screenshots/meshy-mobile-390.png", fullPage: true })
  await page.getByRole("button", { name: "ナビゲーションを開く" }).click()
  await expect(page.getByRole("link", { name: "Meshyflix study", exact: true })).toBeVisible()
})
