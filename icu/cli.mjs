#!/usr/bin/env node
// this_file: icu/cli.mjs
/** Batch JSON bridge: emit one finding list per input, with stable input ordering. */
import { readFileSync } from 'node:fs';
import { checkMessage } from './index.mjs';

try {
  const args = process.argv.slice(2);
  if (args.length > 1 || args.some(arg => arg !== '--components=numbered')) throw new Error('Unknown ICU checker option');
  const options = {components: args.length ? 'numbered' : 'none'};
  const rows = JSON.parse(readFileSync(0, 'utf8'));
  if (!Array.isArray(rows) || rows.length > 100) throw new Error('Expected at most 100 ICU pairs');
  const findings = rows.map(row => checkMessage(row.source, row.target, row.locale, options));
  process.stdout.write(JSON.stringify(findings) + '\n');
} catch (error) {
  process.stderr.write(`ICU check failed: ${error.message}\n`);
  process.exitCode = 2;
}
