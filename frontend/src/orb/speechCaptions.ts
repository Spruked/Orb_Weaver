export type SpeechCaptionProgress = {
  revealedText: string;
  isComplete: boolean;
};

/** Short current thought, replaced as the audio clock advances. */
export function currentSpeechCaption(text: string, currentTime: number, duration: number): string {
  const words: string[] = text.match(/\S+/g) || [];
  const chunks = words.reduce<string[]>((items, word) => {
    const last = items.length - 1;
    if (last < 0 || items[last].length + word.length > 78 || /[.!?]$/.test(items[last])) items.push(word);
    else items[last] += ` ${word}`;
    return items;
  }, []);
  if (!Number.isFinite(duration) || duration <= 0 || currentTime >= duration || currentTime < 0) return '';
  const total = chunks.reduce((n, chunk) => n + chunk.split(' ').length, 0);
  const position = currentTime / duration * total;
  let end = 0;
  return chunks.find(chunk => (end += chunk.split(' ').length) > position) || '';
}

export const canAdvanceCaptionProgression = (playback: { paused: boolean; cancelled: boolean }): boolean =>
  !playback.paused && !playback.cancelled;

const wordCount = (value: string): number => Math.max(1, (value.match(/[\p{L}\p{N}'’]+/gu) || []).length);

/**
 * Keep captions at natural speech boundaries. These phrases are paced by the
 * real audio position, never by an independent typing timer.
 */
export const splitSpeechIntoCaptionPhrases = (text: string): string[] => {
  const sentences = (text || "")
    .replace(/\s+/g, " ")
    .trim()
    .match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [];

  return sentences.flatMap((sentence) => {
    const clauses = sentence
      .trim()
      .split(/(?<=[,;:])\s+(?=[A-Z0-9])/)
      .map((clause) => clause.trim())
      .filter(Boolean);
    return clauses.length ? clauses : [sentence.trim()];
  });
};

export const captionProgressAtPlayback = (
  text: string,
  currentTime: number,
  duration: number,
): SpeechCaptionProgress => {
  const phrases = splitSpeechIntoCaptionPhrases(text);
  if (!phrases.length || !Number.isFinite(currentTime) || !Number.isFinite(duration) || duration <= 0 || currentTime <= 0) {
    return { revealedText: "", isComplete: false };
  }
  if (currentTime >= duration) return { revealedText: phrases.join(" "), isComplete: true };

  const totalWeight = phrases.reduce((sum, phrase) => sum + wordCount(phrase), 0);
  const reachedWeight = (currentTime / duration) * totalWeight;
  let weight = 0;
  const revealed: string[] = [];
  for (const phrase of phrases) {
    const nextWeight = weight + wordCount(phrase);
    if (nextWeight > reachedWeight) break;
    revealed.push(phrase);
    weight = nextWeight;
  }
  return { revealedText: revealed.join(" "), isComplete: false };
};
