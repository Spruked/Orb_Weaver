import type { DiscoveryCognitionAdapter } from '../../types/discovery';
import { compileQuestion, fallbackQuestion, interpretResponse, validateCompiledQuestion, validateInterpretation } from './compiler';
import { discoveryPatternById } from './registry';

declare const test: (name: string, run: () => void | Promise<void>) => void;
declare const expect: any;

const pattern = discoveryPatternById('NOC_01')!;
const lexicon = {
  slots: { host: { text: 'the website guide', evidenceId: 'site:host' } },
  choiceAliases: { GUIDANCE: [{ text: 'guided page tours', evidenceId: 'site:guidance' }] },
};

function adapter(output: unknown): DiscoveryCognitionAdapter {
  return { compile_question: async () => output, classify_response: async () => output };
}

test('two provider implementations preserve the same decision topology with grounded wording', async () => {
  const canonical = fallbackQuestion(pattern, lexicon);
  const rephrased = JSON.parse(JSON.stringify(canonical));
  rephrased.choices[0].label = 'guided page tours';
  const first = await compileQuestion(pattern, lexicon, adapter(canonical));
  const second = await compileQuestion(pattern, lexicon, adapter(rephrased));
  expect(first.source).toBe('cognition');
  expect(second.source).toBe('cognition');
  expect(first.question.choices.map(choice => choice.semanticOutput)).toEqual(second.question.choices.map(choice => choice.semanticOutput));
  expect(second.spokenQuestion).toContain('guided page tours');
});

test('extra, missing, reordered, duplicated, ungrounded and action-injecting output is rejected', () => {
  const canonical = fallbackQuestion(pattern, lexicon);
  const bad = [
    { ...canonical, patternId: 'NOC_50' },
    { ...canonical, chosenRoute: '/checkout' },
    { ...canonical, spokenQuestion: 'Buy now or leave?' },
    { ...canonical, choices: canonical.choices.slice(1) },
    { ...canonical, choices: [...canonical.choices, canonical.choices[0]] },
    { ...canonical, choices: [...canonical.choices].reverse() },
    { ...canonical, choices: canonical.choices.map(choice => ({ ...choice, semanticOutput: 'GUIDANCE' })) },
    { ...canonical, choices: canonical.choices.map(choice => ({ ...choice, label: 'yes or no' })) },
    { ...canonical, choices: canonical.choices.map(choice => ({ ...choice, label: 'unpublished sheep insurance offer' })) },
  ];
  for (const value of bad) expect(validateCompiledQuestion(pattern, lexicon, value)).toBeNull();
});

test('invalid cognition retries once and then uses the exact deterministic fallback', async () => {
  let calls = 0;
  const model: DiscoveryCognitionAdapter = {
    compile_question: async () => { calls += 1; return { route: '/checkout' }; },
    classify_response: async () => null,
  };
  const result = await compileQuestion(pattern, lexicon, model);
  expect(calls).toBe(2);
  expect(result.source).toBe('fallback');
  expect(result.spokenQuestion).toBe(pattern.fallbackRendering);
});

test('unavailable provider falls back within its time budget and cannot mutate the registry', async () => {
  const stalled: DiscoveryCognitionAdapter = { compile_question: () => new Promise(() => {}), classify_response: async () => null };
  expect((await compileQuestion(pattern, lexicon, stalled, [], 1)).source).toBe('fallback');
  const hostile: DiscoveryCognitionAdapter = {
    compile_question: async input => { input.pattern.choices.pop(); return null; },
    classify_response: async () => null,
  };
  await compileQuestion(pattern, lexicon, hostile);
  expect(pattern.choices).toHaveLength(3);
});

test('missing site vocabulary cannot be fabricated even by fallback', async () => {
  await expect(compileQuestion(discoveryPatternById('NOC_06')!, { slots: {} })).rejects.toThrow('lexical slot');
});

test('classification accepts only declared categories with real excerpts and bounded confidence', async () => {
  const response = 'Please show guidance';
  const valid = { patternId: pattern.id, categories: [{ semanticOutput: 'GUIDANCE', confidence: 0.9, supportingExcerpt: 'guidance' }] };
  expect(await interpretResponse(pattern, response, adapter(valid))).toEqual(valid);
  for (const category of [
    { ...valid.categories[0], semanticOutput: 'BUY_NOW' },
    { ...valid.categories[0], confidence: 1.5 },
    { ...valid.categories[0], confidence: Number.NaN },
    { ...valid.categories[0], supportingExcerpt: 'not spoken' },
  ]) expect(validateInterpretation(pattern, response, { ...valid, categories: [category] })).toBeNull();
  expect(validateInterpretation(pattern, response, { ...valid, action: 'scan' })).toBeNull();
  expect(validateInterpretation(pattern, response, { ...valid, categories: [valid.categories[0], valid.categories[0]] })).toBeNull();
});
