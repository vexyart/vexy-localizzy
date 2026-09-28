// this_file: icu/components.mjs
/** Add numbered component events to an already parsed ICU tree, without expansion. */
const selections = new Set(['plural', 'selectordinal', 'select']);
const equal = (left, right) => JSON.stringify(left) === JSON.stringify(right);
const path = stack => stack.map(item => item.id);

function visible(stack, result) {
  stack.forEach((item, index) => {
    if (!item.visible) result.push({type: 'component-content', arg: JSON.stringify(path(stack.slice(0, index + 1)))});
    item.visible = true;
  });
}

function content(token, stack, continued) {
  const result = [];
  const text = value => {
    if (value.trim()) visible(stack, result);
    if (continued && /<\/?\d*$/.test(value)) throw new Error('component tag crosses an ICU token boundary');
    if (value) result.push({...token, value});
  };
  let offset = 0;
  for (const match of token.value.matchAll(/<\/?\d[^<>]*(?:>|$)/g)) {
    if (match.index > offset) text(token.value.slice(offset, match.index));
    const tag = /^<(\/?)(\d+)(\/?)>$/.exec(match[0]);
    if (!tag || (tag[1] && tag[3])) throw new Error('malformed numbered component tag');
    const [, close, id, self] = tag;
    if (close && stack.pop()?.id !== id) throw new Error('mismatched numbered component closing tag');
    if (self) visible(stack, result);
    result.push({type: 'component', arg: JSON.stringify([close ? 'close' : self ? 'void' : 'open', id, path(stack)])});
    if (!close && !self) stack.push({id, visible: false});
    offset = match.index + match[0].length;
  }
  if (offset < token.value.length) text(token.value.slice(offset));
  return result;
}

function walk(tokens, stack, continued = false) {
  const result = [];
  for (const [index, token] of tokens.entries()) {
    const follows = continued || index < tokens.length - 1;
    if (token.type === 'content') {
      result.push(...content(token, stack, follows));
      continue;
    }
    const scoped = {...token, componentPath: path(stack)};
    if (selections.has(token.type)) {
      const endings = [];
      scoped.cases = token.cases.map(branch => {
        const branchStack = stack.map(item => ({...item}));
        const translated = walk(branch.tokens, branchStack, follows);
        endings.push(branchStack);
        return {...branch, tokens: translated};
      });
      if (endings.some(ending => !equal(path(ending), path(endings[0])))) {
        throw new Error('selector branches leave inconsistent numbered component nesting');
      }
      if (endings.length) stack.splice(0, stack.length, ...endings[0].map((item, index) =>
        ({id: item.id, visible: endings.every(ending => ending[index].visible)})));
    } else visible(stack, result);
    result.push(scoped);
  }
  return result;
}

export function numberedComponents(tokens) {
  const stack = [];
  const result = walk(tokens, stack);
  if (stack.length) throw new Error('unclosed numbered component tag');
  return result;
}
