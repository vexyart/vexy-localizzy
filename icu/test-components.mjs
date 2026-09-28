// this_file: icu/test-components.mjs
import assert from 'node:assert/strict';
import test from 'node:test';
import { spawnSync } from 'node:child_process';
import { checkMessage } from './index.mjs';

const check = (source, target, locale = 'en') => checkMessage(source, target, locale, {components: 'numbered'});
for (const [name, source, target, locale] of [
  ['translated link', 'Read <0>instructions</0>.', 'Czytaj <0>instrukcję</0>.'],
  ['plain comparison sign', 'Less than <', 'Mniejsze <'],
  ['sibling reorder', '<0>Read</0> <1>Help</1>', '<1>Pomoc</1> <0>Czytaj</0>'],
  ['nested and repeated', '<0><1>{x}</1></0> <0>Again</0>', '<0>Ponownie</0> <0><1>{x}</1></0>'],
  ['self closing', 'A <0/> B <1/>', 'B <1/> A <0/>'],
  ['outside selector', '<0>{n, plural, one{One}other{#}}</0>', '<0>{n, plural, one{Jeden}few{#}many{#}other{#}}</0>', 'pl'],
  ['new locale branches', '{n, plural, one{<0>One</0>}other{<1>#</1>}}', '{n, plural, one{<0>Jeden</0>}few{<1>#</1>}many{<1>#</1>}other{<1>#</1>}}', 'pl'],
  ['open before branch close', '<0>{x, select, a{A</0>}other{B</0>}}', '<0>{x, select, a{AA</0>}other{BB</0>}}'],
  ['open in branches close after', '{x, select, a{<0>A}other{<0>B}}</0>', '{x, select, other{<0>BB}a{<0>AA}}</0>'],
  ['same selector reordered', '{x, select, a{<0>A</0>}other{B}} {x, select, a{<1>A</1>}other{C}}', '{x, select, a{<1>AA</1>}other{CC}} {x, select, a{<0>AA</0>}other{BB}}'],
  ['quoted braces', "<0>'{literal}' {name}</0>", "<0>'{dosłowne}' {name}</0>"],
]) {
  test(`numbered components accept ${name}`, () => assert.deepEqual(check(source, target, locale), []));
}

for (const [name, source, target, locale] of [
  ['loss', 'Read <0>instructions</0>', 'Read instructions'],
  ['invention', 'Read instructions', 'Read <0>instructions</0>'],
  ['identity change', '<0>A</0>', '<1>A</1>'],
  ['duplicate', '<0>A</0>', '<0>A</0><0>A</0>'],
  ['nesting change', '<0><1>A</1></0>', '<1><0>A</0></1>'],
  ['argument moved out', '<0>{name}</0>', '<0>A</0>{name}'],
  ['missing close', '<0>A</0>', '<0>A'],
  ['crossed closes', '<0><1>A</1></0>', '<0><1>A</0></1>'],
  ['malformed tag', '<0>A</0>', '<0 name="x">A</0>'],
  ['spaced self closing', 'A <0/>', 'A <0 />'],
  ['empty component prose', '<0>Read</0>', '<0></0>'],
  ['empty label with outside prose', 'Read <0>instructions</0>.', 'Czytaj instrukcję<0></0>.'],
  ['one repeated label emptied', '<0>A</0> <0>B</0>', '<0>A B</0> <0></0>'],
  ['selector manufactures tag', '{x,select,a {First}other {Second}}', '<{x,select,a {0/}other {0/}}>'],
  ['branch manufactures tag', '{x,select,a {First}other {Second}}', '{x,select,a {<0}other {<0}}/>'],
  ['paired changed to void', '<0>A</0>', '<0/> A'],
  ['branch loss', '{x, select, a{<0>A</0>}other{B}}', '{x, select, a{A}other{B}}'],
  ['branch swap', '{x, select, a{<0>A</0>}other{<1>B</1>}}', '{x, select, a{<1>A</1>}other{<0>B</0>}}'],
  ['expanded branch wrong component', '{n, plural, one{<0>A</0>}other{<1>#</1>}}', '{n, plural, one{<0>A</0>}few{<0>#</0>}many{<1>#</1>}other{<1>#</1>}}', 'pl'],
  ['inconsistent branch nesting', '{x, select, a{<0>A}other{<0>B}}</0>', '{x, select, a{<0>A}other{<1>B}}</0>'],
  ['invalid source', '<0>A', '<0>A</0>'],
]) {
  test(`numbered components reject ${name}`, () => assert.ok(check(source, target, locale).length));
}

test('numbered components are opt-in', () => {
  assert.deepEqual(checkMessage('<0>A</0>', 'B', 'en'), []);
  assert.throws(() => checkMessage('A', 'B', 'en', {components: 'unknown'}), /component/i);
});

test('CLI enables numbered components for the unchanged Python batch protocol', () => {
  const result = spawnSync(process.execPath, [new URL('./cli.mjs', import.meta.url).pathname, '--components=numbered'], {
    input: JSON.stringify([{source: '<0>A</0>', target: 'B', locale: 'en'}]), encoding: 'utf8'});
  assert.equal(result.status, 0);
  assert.ok(JSON.parse(result.stdout)[0].length);
});
