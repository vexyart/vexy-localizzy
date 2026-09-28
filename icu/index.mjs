// this_file: icu/index.mjs
/** Structural checks; parsing and apostrophe semantics belong to the published parser. */
import { parse } from '@messageformat/parser';
import { numberedComponents } from './components.mjs';

const selections = new Set(['plural', 'selectordinal', 'select']);
const canonical = (value) => JSON.stringify(value, (key, item) => key === 'ctx' ? undefined : item);
const same = (left, right) => canonical([...left].sort()) === canonical([...right].sort());

function signature(token) {
  if (token.type === 'function') {
    const param = token.param ?? [];
    const style = param.every(t => t.type === 'content')
      ? param.map(t => t.value).join('').trim() : canonical(param);
    return canonical([token.type, token.arg, token.key, style, token.componentPath ?? []]);
  }
  return canonical([token.type, token.arg, token.pluralOffset ?? 0, token.componentPath ?? []]);
}

function structural(tokens) {
  return tokens.filter(t => t.type !== 'content').sort((a, b) =>
    signature(a).localeCompare(signature(b), 'en'));
}

function validateTree(tokens, categories, target, path, findings) {
  for (const token of tokens) {
    if (token.type === 'function') {
      validateTree(token.param ?? [], categories, target, path, findings);
    }
    if (!selections.has(token.type)) continue;
    const keys = token.cases.map(c => c.key);
    const at = `${path}/${token.arg}:${token.type}`;
    // The published parser overwrites repeated offsets; its retained header
    // context is the only place their original multiplicity remains visible.
    const header = token.ctx.text.slice(token.ctx.text.indexOf(',') + 1);
    if ((header.match(/offset\s*:\s*\d+/g) ?? []).length > 1) {
      findings.push(`${at}: duplicate plural offset`);
    }
    if (!keys.includes('other') || new Set(keys).size !== keys.length) {
      findings.push(`${at}: require unique cases and an other case`);
    }
    if (target && token.type !== 'select') {
      const required = categories[token.type];
      if (required.some(key => !keys.includes(key))) {
        findings.push(`${at}: missing locale cases ${required.filter(key => !keys.includes(key)).join(', ')}`);
      }
    }
    for (const branch of token.cases) {
      validateTree(branch.tokens, categories, target, `${at}/${branch.key}`, findings);
    }
  }
}

function compareBranches(source, target, categories, path, findings) {
  const original = new Map(source.cases.map(c => [c.key, c.tokens]));
  const translated = new Map(target.cases.map(c => [c.key, c.tokens]));
  const protectedKeys = keys => source.type === 'select' ? [...keys] : [...keys].filter(k => k.startsWith('='));
  if (!same(protectedKeys(original.keys()), protectedKeys(translated.keys()))) {
    findings.push(`${path}: select or exact-number cases differ`);
    return;
  }
  for (const [key, tokens] of translated) {
    const reference = original.get(key) ?? original.get('other');
    if (reference) compareTokens(reference, tokens, categories, `${path}/${key}`, findings);
  }
}

function compareTokens(source, target, categories, path, findings) {
  const left = structural(source), right = structural(target);
  if (!same(left.map(signature), right.map(signature))) {
    findings.push(`${path}: argument names, counts, formats or plural offsets differ`);
    return;
  }
  const visible = tokens => tokens.some(t => !t.type.startsWith('component') && (t.type !== 'content' || t.value.trim()));
  if (visible(source) && !visible(target)) {
    findings.push(`${path}: translation branch is blank`);
  }
  const selected = left.filter(t => selections.has(t.type));
  const alternatives = right.filter(t => selections.has(t.type));
  const edges = selected.map(token => alternatives.flatMap((candidate, index) => {
    if (signature(token) !== signature(candidate)) return [];
    const issues = [];
    compareBranches(token, candidate, categories, path, issues);
    return issues.length ? [] : [index];
  }));
  const owners = new Map();
  function assign(index, seen) {
    for (const candidate of edges[index]) {
      if (seen.has(candidate)) continue;
      seen.add(candidate);
      if (!owners.has(candidate) || assign(owners.get(candidate), seen)) {
        owners.set(candidate, index);
        return true;
      }
    }
    return false;
  }
  for (let index = 0; index < selected.length; index += 1) {
    if (!assign(index, new Set())) findings.push(`${path}/${selected[index].arg}: selector branch contracts differ`);
  }
}

/** Return structural findings; invalid configuration throws before checking text.
 * New plural categories inherit the source's other-branch argument contract.
 * Numbered rich-text components are opt-in; named markup remains caller-owned.
 * This does not validate terminology or runtime custom formatters.
 */
export function checkMessage(source, target, locale, {components = 'none'} = {}) {
  if (!['none', 'numbered'].includes(components)) throw new RangeError('Unknown component policy');
  if (typeof source !== 'string' || typeof target !== 'string') {
    throw new TypeError('ICU source and target must be strings');
  }
  if (typeof locale !== 'string' || !locale || !Intl.PluralRules.supportedLocalesOf([locale]).length) {
    throw new RangeError('A supported ICU target locale is required');
  }
  const categories = Object.fromEntries(['cardinal', 'ordinal'].map(type => [
    type === 'cardinal' ? 'plural' : 'selectordinal',
    new Intl.PluralRules(locale, { type }).resolvedOptions().pluralCategories,
  ]));
  let left, right;
  try { left = parse(source); } catch { return ['source: malformed ICU syntax']; }
  try { right = parse(target); } catch { return ['target: malformed ICU syntax']; }
  if (components === 'numbered') {
    try { left = numberedComponents(left); } catch (error) { return [`source: ${error.message}`]; }
    try { right = numberedComponents(right); } catch (error) { return [`target: ${error.message}`]; }
  }
  const findings = [];
  validateTree(left, categories, false, 'source', findings);
  validateTree(right, categories, true, 'target', findings);
  if (!findings.length) compareTokens(left, right, categories, 'message', findings);
  return findings;
}
