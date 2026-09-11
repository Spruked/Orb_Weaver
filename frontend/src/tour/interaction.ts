import { LANDING_TOUR_CHAPTERS } from './curriculum';
import type { TourEngagementQuestion, TourSemanticCategory, TourStop } from '../types/tour';

export type EngagementSelection = {
  question: TourEngagementQuestion;
  optionId: string;
  semanticCategory: TourSemanticCategory;
};

export function engagementForStop(stop: TourStop, askedQuestionIds: string[]): TourEngagementQuestion | null {
  const question = stop.engagementQuestion;
  return question && !askedQuestionIds.includes(question.id) ? question : null;
}

export function engagementById(questionId: string | null): TourEngagementQuestion | null {
  if (!questionId) return null;
  for (const chapter of LANDING_TOUR_CHAPTERS) {
    const question = chapter.stops.find((stop) => stop.engagementQuestion?.id === questionId)?.engagementQuestion;
    if (question) return question;
  }
  return null;
}

export function classifyEngagementAnswer(question: TourEngagementQuestion, answer: string): EngagementSelection | null {
  const normalized = answer.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
  if (!normalized) return null;
  const option = question.options
    .map((candidate) => ({ candidate, score: candidate.keywords.reduce((score, keyword) => score + (normalized.includes(keyword) ? 1 : 0), 0) }))
    .sort((left, right) => right.score - left.score)[0];
  if (!option || option.score <= 0) return null;
  return { question, optionId: option.candidate.id, semanticCategory: option.candidate.semanticCategory };
}
