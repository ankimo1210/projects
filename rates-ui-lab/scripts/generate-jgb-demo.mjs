import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const TENORS = [2, 5, 7, 10, 20, 30, 40];
const FINAL_YIELDS = [0.92, 1.28, 1.54, 1.85, 2.34, 2.51, 2.63];
const FINAL_DATE = "2026-09-04";
const OBSERVATION_COUNT = 60;

export const DATASET_FILENAMES = [
  "jgb-demo.json",
  "jgb-demo-missing.json",
  "jgb-demo-negative.json",
  "jgb-demo-flat.json",
];

const roundSourceValue = (value) => Number(value.toFixed(3));

const makeWeekdayDates = (count, finalDate) => {
  const dates = [];
  const cursor = new Date(`${finalDate}T00:00:00.000Z`);
  while (dates.length < count) {
    const weekday = cursor.getUTCDay();
    if (weekday >= 1 && weekday <= 5)
      dates.push(cursor.toISOString().slice(0, 10));
    cursor.setUTCDate(cursor.getUTCDate() - 1);
  }
  return dates.reverse();
};

const metadata = (sourceLabel, snapshots) => ({
  schemaVersion: 1,
  dataKind: "synthetic",
  currency: "JPY",
  curve: "JGB",
  sourceLabel,
  snapshots,
});

export function generateCanonicalDataset() {
  const dates = makeWeekdayDates(OBSERVATION_COUNT, FINAL_DATE);
  const lastIndex = dates.length - 1;
  const snapshots = dates.map((date, observationIndex) => {
    const distance = lastIndex - observationIndex;
    const levelMove = -0.002 * distance + 0.028 * Math.sin(distance * 0.41);
    const twistCycle = Math.sin(distance * 0.23);
    return {
      date,
      points: TENORS.map((tenorYears, tenorIndex) => ({
        tenorYears,
        yieldPct: roundSourceValue(
          FINAL_YIELDS[tenorIndex] +
            levelMove +
            0.004 * (tenorIndex - 3) * twistCycle,
        ),
      })),
    };
  });

  return metadata(
    "Synthetic JGB curve for local UI comparison; not market data",
    snapshots,
  );
}

export function generateFixtureDatasets() {
  const missing = structuredClone(generateCanonicalDataset());
  missing.sourceLabel = "Synthetic JGB missing-value fixture; not market data";
  missing.snapshots
    .at(-1)
    .points.find((point) => point.tenorYears === 10).yieldPct = null;
  missing.snapshots
    .at(-2)
    .points.find((point) => point.tenorYears === 2).yieldPct = null;
  missing.snapshots
    .at(-6)
    .points.find((point) => point.tenorYears === 30).yieldPct = null;

  const negative = structuredClone(generateCanonicalDataset());
  negative.sourceLabel = "Synthetic JGB negative-rate fixture; not market data";
  negative.snapshots = negative.snapshots.map((snapshot) => ({
    ...snapshot,
    points: snapshot.points.map((point) => ({
      ...point,
      yieldPct: roundSourceValue(point.yieldPct - 1.1),
    })),
  }));

  const flat = structuredClone(generateCanonicalDataset());
  flat.sourceLabel = "Synthetic JGB flat-curve fixture; not market data";
  flat.snapshots = flat.snapshots.map((snapshot) => {
    const flatYield = snapshot.points.find(
      (point) => point.tenorYears === 10,
    ).yieldPct;
    return {
      ...snapshot,
      points: snapshot.points.map((point) => ({
        ...point,
        yieldPct: flatYield,
      })),
    };
  });

  return { missing, negative, flat };
}

export function serializeDataset(dataset) {
  return `${JSON.stringify(dataset, null, 2)}\n`;
}

export async function writeDatasets(projectRoot) {
  const canonicalDirectory = join(projectRoot, "data");
  const appDirectory = join(
    projectRoot,
    "experiments",
    "tremor-dashboard",
    "src",
    "data",
    "rates",
  );
  await Promise.all([
    mkdir(canonicalDirectory, { recursive: true }),
    mkdir(appDirectory, { recursive: true }),
  ]);

  const fixtures = generateFixtureDatasets();
  const datasets = [
    generateCanonicalDataset(),
    fixtures.missing,
    fixtures.negative,
    fixtures.flat,
  ];
  await Promise.all(
    DATASET_FILENAMES.flatMap((filename, index) => {
      const contents = serializeDataset(datasets[index]);
      return [
        writeFile(join(canonicalDirectory, filename), contents, "utf8"),
        writeFile(join(appDirectory, filename), contents, "utf8"),
      ];
    }),
  );
}

const scriptPath = fileURLToPath(import.meta.url);
if (process.argv[1] !== undefined && resolve(process.argv[1]) === scriptPath) {
  const projectRoot = resolve(dirname(scriptPath), "..");
  await writeDatasets(projectRoot);
}
