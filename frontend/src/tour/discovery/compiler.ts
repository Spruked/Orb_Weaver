import type {
  CompiledChoiceProposal, DiscoveryCognitionAdapter, DiscoveryLexicon,
  DiscoveryPattern, InterpretedResponse,
} from '../../types/discovery';

const record = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value);
const keysAre = (value: Record<string, unknown>, keys: string[]): boolean =>
  Object.keys(value).length === keys.length && keys.every(key => Object.prototype.hasOwnProperty.call(value, key));
const copy = <T,>(value: T): T => JSON.parse(JSON.stringify(value));

function renderSlots(template: string, lexicon: DiscoveryLexicon): string {
  return template.replace(/\{([a-z_]+)\}/g, (_, slot: string) => {
    const value = lexicon.slots[slot];
    if (!value?.evidenceId?.trim() || !value.text.trim() || value.text.length > 80 ||
      /[{}?<>`,\r\n]|\bor\b/i.test(value.text)) throw new Error(`Missing or invalid grounded lexical slot: ${slot}`);
    return value.text;
  });
}

function allowedLabels(pattern: DiscoveryPattern, index: number, lexicon: DiscoveryLexicon): string[] {
  const choice = pattern.choices[index];
  const aliases = lexicon.choiceAliases?.[choice.semanticOutput] || [];
  return [renderSlots(choice.fallbackLabel, lexicon), ...aliases.filter(alias =>
    alias.evidenceId?.trim() && alias.text.trim() && alias.text.length <= 200 &&
    !/[{}?<>`,\r\n]|\b(?:or|yes|no)\b/i.test(alias.text),
  ).map(alias => alias.text)];
}

/** Model output cannot introduce speech outside the canonical question frame. */
export function validateCompiledQuestion(
  pattern: DiscoveryPattern, lexicon: DiscoveryLexicon, value: unknown,
): CompiledChoiceProposal | null {
  if (!record(value) || !keysAre(value, ['patternId', 'choices']) || value.patternId !== pattern.id ||
    !Array.isArray(value.choices) || value.choices.length !== pattern.choices.length) return null;
  const labels = new Set<string>();
  for (let index = 0; index < value.choices.length; index += 1) {
    const choice = value.choices[index];
    if (!record(choice) || !keysAre(choice, ['semanticOutput', 'label']) ||
      choice.semanticOutput !== pattern.choices[index].semanticOutput || typeof choice.label !== 'string' ||
      labels.has(choice.label.toLowerCase()) || !allowedLabels(pattern, index, lexicon).includes(choice.label)) return null;
    labels.add(choice.label.toLowerCase());
  }
  return copy(value) as unknown as CompiledChoiceProposal;
}

export function fallbackQuestion(pattern: DiscoveryPattern, lexicon: DiscoveryLexicon): CompiledChoiceProposal {
  return {
    patternId: pattern.id,
    choices: pattern.choices.map(choice => ({
      semanticOutput: choice.semanticOutput, label: renderSlots(choice.fallbackLabel, lexicon),
    })),
  };
}

export function renderQuestion(pattern: DiscoveryPattern, lexicon: DiscoveryLexicon, proposal: unknown): string {
  const valid = validateCompiledQuestion(pattern, lexicon, proposal);
  if (!valid) throw new Error('Question topology or lexical grounding is invalid');
  const labels = valid.choices.map(choice => choice.label);
  return `${renderSlots(pattern.fallbackStem, lexicon)} — ${labels.slice(0, -1).join(', ')}, or ${labels[labels.length - 1]}?`;
}

async function boundedCall<T>(call: () => Promise<T>, timeoutMs: number): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      Promise.resolve().then(call),
      new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new Error('Cognition timeout')), timeoutMs); }),
    ]);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}

export async function compileQuestion(
  pattern: DiscoveryPattern, lexicon: DiscoveryLexicon, adapter?: DiscoveryCognitionAdapter,
  relevantContext: readonly string[] = [], timeoutMs = 2500,
): Promise<{ question: CompiledChoiceProposal; spokenQuestion: string; source: 'cognition' | 'fallback'; attempts: number }> {
  // A missing slot is a caller error: don't invent site vocabulary on fallback.
  const fallback = fallbackQuestion(pattern, lexicon);
  const fallbackSpeech = renderQuestion(pattern, lexicon, fallback);
  let attempts = 0;
  if (adapter) {
    for (attempts = 1; attempts <= 2; attempts += 1) {
      try {
        const proposal = await boundedCall(() => adapter.compile_question(copy({ pattern, lexicon, relevantContext })), timeoutMs);
        const valid = validateCompiledQuestion(pattern, lexicon, proposal);
        if (valid) return { question: valid, spokenQuestion: renderQuestion(pattern, lexicon, valid), source: 'cognition', attempts };
      } catch {
        // Malformed/failed cognition consumes an attempt, never authority.
      }
    }
  }
  return { question: fallback, spokenQuestion: fallbackSpeech, source: 'fallback', attempts: adapter ? 2 : 0 };
}

export function validateInterpretation(pattern: DiscoveryPattern, visitorResponse: string, value: unknown): InterpretedResponse | null {
  if (!record(value) || !keysAre(value, ['patternId', 'categories']) || value.patternId !== pattern.id ||
    !Array.isArray(value.categories) || value.categories.length > pattern.choices.length) return null;
  const allowed = new Set(pattern.choices.map(choice => choice.semanticOutput));
  const seen = new Set<string>();
  for (const item of value.categories) {
    if (!record(item) || !keysAre(item, ['semanticOutput', 'confidence', 'supportingExcerpt']) ||
      typeof item.semanticOutput !== 'string' || !allowed.has(item.semanticOutput) || seen.has(item.semanticOutput) ||
      typeof item.confidence !== 'number' || !Number.isFinite(item.confidence) || item.confidence < 0 || item.confidence > 1 ||
      typeof item.supportingExcerpt !== 'string' || !item.supportingExcerpt.trim() || !visitorResponse.includes(item.supportingExcerpt)) return null;
    seen.add(item.semanticOutput);
  }
  return copy(value) as unknown as InterpretedResponse;
}

export async function interpretResponse(
  pattern: DiscoveryPattern, visitorResponse: string, adapter: DiscoveryCognitionAdapter, timeoutMs = 2500,
): Promise<InterpretedResponse | null> {
  try {
    const result = await boundedCall(() => adapter.classify_response({
      patternId: pattern.id, allowedSemanticOutputs: pattern.choices.map(choice => choice.semanticOutput), visitorResponse,
    }), timeoutMs);
    return validateInterpretation(pattern, visitorResponse, result);
  } catch { return null; }
}
