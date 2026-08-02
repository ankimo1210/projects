import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const projectRoot = new URL("../", import.meta.url);

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the Japanese SDE textbook shell", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<html[^>]*lang="ja"/i);
  assert.match(html, /<title>Stochastic — 不確かな世界の微分方程式<\/title>/i);
  assert.match(html, /なぜ確率微分方程式が必要なのか/);
  assert.match(html, /ODE・初期値不確実性・SDE の比較/);
  assert.match(html, /この章でできるようになること/);
  assert.match(html, /WHAT TO NOTICE/);
  assert.match(html, /P と Q/);
  assert.match(html, /Langevin 力学/);
  assert.match(html, /モデル批判/);
  assert.match(html, /本文へ移動/);
  assert.match(html, /aria-label="ODE・初期値不確実性・SDE の比較。/);
  assert.match(html, /property="og:image" content="http:\/\/localhost\/og\.png"/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape|react-loading-skeleton/i);
});

test("keeps the textbook structured and the starter preview removed", async () => {
  const [
    coreChapters,
    chaptersPartVVI,
    chaptersPartVII,
    chaptersPartVIIIIX,
    textbook,
    extendedLabs,
    applicationLabs,
    page,
    layout,
    packageJson,
    hosting,
  ] = await Promise.all([
    readFile(new URL("../content/chapters.ts", import.meta.url), "utf8"),
    readFile(new URL("../content/chapters-part-v-vi.ts", import.meta.url), "utf8"),
    readFile(new URL("../content/chapters-part-vii.ts", import.meta.url), "utf8"),
    readFile(new URL("../content/chapters-part-viii-ix.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/sde-textbook.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/extended-labs.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/application-labs.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
    readFile(new URL("../.openai/hosting.json", import.meta.url), "utf8"),
  ]);

  const chapterSource = [coreChapters, chaptersPartVVI, chaptersPartVII, chaptersPartVIIIIX].join("\n");
  const chapterNumbers = [...chapterSource.matchAll(/\n    number: (\d+),/g)]
    .map((match) => Number(match[1]))
    .sort((left, right) => left - right);
  const chapterIds = [...chapterSource.matchAll(/\n    id: "([^"]+)",/g)].map((match) => match[1]);
  const chapterLabs = [...chapterSource.matchAll(/\n    lab: "([^"]+)",/g)].map((match) => match[1]);
  assert.deepEqual(chapterNumbers, Array.from({ length: 47 }, (_, index) => index + 1));
  assert.equal(chapterIds.length, 47);
  assert.equal(new Set(chapterIds).size, 47);
  assert.equal(chapterLabs.length, 47);
  for (const marker of [
    /\n    objectives: \[/g,
    /\n    sections: \[/g,
    /\n    formulaLabel:/g,
    /\n    labTitle:/g,
    /\n    labObjective:/g,
    /\n    notice: \[/g,
    /\n    exercise: \{/g,
    /\n    next:/g,
  ]) {
    assert.equal((chapterSource.match(marker) ?? []).length, 47);
  }
  const labKindBlock = coreChapters.match(
    /export type LabKind =([\s\S]*?);\n\nexport type Chapter/,
  )?.[1] ?? "";
  const declaredLabs = [...labKindBlock.matchAll(/\| "([^"]+)"/g)].map((match) => match[1]);
  assert.deepEqual(
    [...new Set(chapterLabs)].sort(),
    [...declaredLabs].sort(),
  );
  assert.ok((coreChapters.match(/\n    term: "/g) ?? []).length >= 20);
  assert.match(chapterSource, /why-sdes/);
  assert.match(chapterSource, /probability-over-time/);
  assert.match(chapterSource, /brownian-roughness/);
  assert.match(chapterSource, /stochastic-integration/);
  assert.match(chapterSource, /reading-an-sde/);
  assert.match(chapterSource, /arithmetic-brownian-motion/);
  assert.match(chapterSource, /cir-square-root-diffusion/);
  assert.match(chapterSource, /multidimensional-correlation/);
  assert.match(chapterSource, /infinitesimal-generator/);
  assert.match(chapterSource, /kolmogorov-backward-equation/);
  assert.match(chapterSource, /quadratic-variation/);
  assert.match(chapterSource, /feynman-kac/);
  assert.match(chapterSource, /first-passage-times/);
  assert.match(chapterSource, /measure-change/);
  assert.match(chapterSource, /langevin-dynamics/);
  assert.match(chapterSource, /model-criticism/);
  assert.match(chapterSource, /sde-model-synthesis/);
  assert.match(textbook, /drawSdeOverview/);
  assert.match(textbook, /drawPathDistribution/);
  assert.match(textbook, /drawDriftDiffusion/);
  assert.match(textbook, /drawArithmeticBrownian/);
  assert.match(textbook, /drawCir/);
  assert.match(textbook, /drawGenerator/);
  assert.match(textbook, /drawBackwardEquation/);
  assert.match(textbook, /drawFeynmanKac/);
  assert.match(textbook, /drawFirstPassage/);
  assert.match(textbook, /functionChoice/);
  assert.match(textbook, /eulerConvergence/);
  assert.match(textbook, /measureChangeDiagnostics/);
  assert.match(textbook, /roughnessDiagnostics/);
  assert.match(textbook, /stochasticIntegralDiagnostics/);
  assert.match(textbook, /correlatedBrownianDiagnostics/);
  assert.match(extendedLabs, /drawFractionalBrownian/);
  assert.match(extendedLabs, /drawMilstein/);
  assert.match(extendedLabs, /drawDeltaHedging/);
  assert.match(extendedLabs, /drawForwardCurve/);
  assert.match(extendedLabs, /drawApplicationLab/);
  assert.match(applicationLabs, /drawLangevin/);
  assert.match(applicationLabs, /drawChemicalReaction/);
  assert.match(applicationLabs, /drawEpidemic/);
  assert.match(applicationLabs, /drawFiltering/);
  assert.match(applicationLabs, /drawModelCriticism/);
  assert.match(applicationLabs, /drawSdeSynthesis/);
  const renderers = [textbook, extendedLabs, applicationLabs].join("\n");
  for (const lab of new Set(chapterLabs)) {
    assert.match(renderers, new RegExp(`case "${lab}"`), `missing renderer for ${lab}`);
  }
  assert.match(page, /<SDETextbook \/>/);
  assert.match(layout, /lang="ja"/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
  assert.deepEqual(JSON.parse(hosting), { d1: null, r2: null });
  await assert.rejects(access(new URL("../app/_sites-preview", import.meta.url)));
  await assert.doesNotReject(access(projectRoot));
});
