// this_file: icu/test.mjs
import assert from 'node:assert/strict';
import test from 'node:test';
import { spawnSync } from 'node:child_process';
import { checkMessage } from './index.mjs';

const english = '{count, plural, one {One item} other {# items for {name}}}';
const polish = '{count, plural, one {Jeden element} few {# elementy dla {name}} many {# elementów dla {name}} other {# elementu dla {name}}}';

for (const [name, source, target, locale] of [
  ['reordered arguments', '{first} meets {second}', '{second} spotyka {first}', 'pl'],
  ['Polish categories', english, polish, 'pl'],
  ['Japanese categories', english, '{count, plural, other {{name}: #}}', 'ja'],
  ['quoted braces', "'{literal}' {name}", "'{dosłowne}' {name}", 'pl'],
  ['number format', '{value, number, ::currency/USD}', 'Cena: {value, number, ::currency/USD}', 'pl'],
  ['nested select', '{kind, select, a {{n, plural, one {One} other {#}}} other {{name}}}', '{kind, select, a {{n, plural, one {Un} other {#}}} other {{name}}}', 'en'],
  ['ordinal', '{n, selectordinal, one {#st} two {#nd} few {#rd} other {#th}}', '{n, selectordinal, other {#}}', 'pl'],
  ['literal hash', 'Hash # {name}', 'Skrót # {name}', 'pl'],
]) {
  test(`accept ${name}`, () => assert.deepEqual(checkMessage(source, target, locale), []));
}

for (const [name, source, target, locale = 'pl'] of [
  ['missing argument', 'Hello {name}', 'Cześć'],
  ['renamed argument', 'Hello {name}', 'Cześć {imię}'],
  ['duplicate argument', '{name}', '{name} {name}'],
  ['syntax', '{name}', '{name'],
  ['invalid source', '{name', '{name}'],
  ['missing plural categories', english, '{count, plural, one {Jeden element} other {# elementów dla {name}}}'],
  ['missing other', '{n, plural, other {#}}', '{n, plural, one {#}}'],
  ['changed exact selector', '{n, plural, =0 {Zero} other {#}}', '{n, plural, =1 {Jeden} one {#} few {#} many {#} other {#}}'],
  ['changed offset', '{n, plural, offset:1 other {#}}', '{n, plural, offset:2 one {#} few {#} many {#} other {#}}'],
  ['changed select keys', '{kind, select, a {A} other {B}}', '{kind, select, b {A} other {B}}'],
  ['branch placeholder loss', english, polish.replace('elementy dla {name}', 'elementy')],
  ['branch number loss', english, polish.replace('# elementy', 'elementy')],
  ['duplicate branch', '{n, plural, other {#}}', '{n, plural, other {#} other {#}}', 'ja'],
  ['duplicate offset', '{n, plural, one {A} other {B}}', '{n, plural, offset:0 offset:0 one {A} other {B}}', 'en'],
  ['formatter change', '{value, number, ::currency/USD}', '{value, number, ::currency/EUR}'],
  ['argument type change', '{value}', '{value, number}'],
  ['blank branch', '{kind, select, a {A} other {B}}', '{kind, select, a {} other {B}}'],
]) {
  test(`reject ${name}`, () => assert.ok(checkMessage(source, target, locale).length > 0));
}

test('reject unsupported locale instead of silently using host locale', () => {
  assert.throws(() => checkMessage('Hello', 'Cześć', 'zz'), /locale/i);
});

test('accept reordered repeated selectors with distinct branch contracts', () => {
  const a = '{kind, select, a {{x}} other {{y}}}';
  const b = '{kind, select, a {{y}} other {{x}}}';
  assert.deepEqual(checkMessage(`${a} ${b}`, `${b} ${a}`, 'en'), []);
});

test('CLI returns ordered findings for a whole batch', () => {
  const input = JSON.stringify([{source: '{x}', target: '{x}', locale: 'pl'}, {source: '{x}', target: 'x', locale: 'pl'}]);
  const result = spawnSync(process.execPath, [new URL('./cli.mjs', import.meta.url).pathname], {input, encoding: 'utf8'});
  assert.equal(result.status, 0);
  const rows = JSON.parse(result.stdout);
  assert.deepEqual(rows[0], []);
  assert.equal(rows[1].length, 1);
});

for (const input of ['invalid', '{}', '[null]', JSON.stringify(Array(101).fill({source:'a', target:'b', locale:'pl'}))]) {
  test(`CLI rejects invalid input ${input.slice(0, 12)}`, () => {
    const result = spawnSync(process.execPath, [new URL('./cli.mjs', import.meta.url).pathname], {input, encoding:'utf8'});
    assert.equal(result.status, 2);
    assert.equal(result.stdout, '');
  });
}
