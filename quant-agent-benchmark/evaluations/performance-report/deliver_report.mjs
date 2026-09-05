#!/usr/bin/env node
// Thin invocation of the installed canonical renderer, not a second renderer.
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const builder = process.argv[2];
if (!builder) throw new Error('Usage: node deliver_report.mjs <installed deliver_portable_artifact.mjs>');
const output = execFileSync(process.execPath, [builder,
  '--input', resolve(here, 'artifact.json'),
  '--output', resolve(here, '../performance_report.html')], { encoding: 'utf8' });
const receipt = JSON.parse(output.trim());
if (!receipt.ok) throw new Error(output);
receipt.visual_qa_limitation = receipt.stages?.verification === 'passed' ? null
  : 'The packaged verifier completed structural checks only. The updated seven-model HTML has not passed browser-level layout/source-dialog QA. Earlier four-model manual QA does not certify the expanded report. Semantic table fallbacks are retained; no browser was installed.';
writeFileSync(resolve(here, 'delivery-receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
const artifact = JSON.parse(readFileSync(resolve(here, 'artifact.json')));
console.log(JSON.stringify({ ...receipt, canonicalCharts: artifact.manifest.charts.length,
  canonicalTables: artifact.manifest.tables.length }));
