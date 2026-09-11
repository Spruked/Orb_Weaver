import { classifyEngagementAnswer, engagementById } from './interaction';
import { LANDING_TOUR_CHAPTERS } from './curriculum';

declare const test: (name: string, run: () => void | Promise<void>) => void;
declare const expect: any;

test('a discovery answer produces an authored semantic category, not a route', () => {
  const question = engagementById('discovery-or-guidance');
  expect(question).not.toBeNull();
  expect(classifyEngagementAnswer(question!, 'I want to understand what it discovers about the site.')).toMatchObject({
    optionId: 'discovery',
    semanticCategory: 'SITE_DISCOVERY',
  });
});

test('a guidance answer produces an authored semantic category, not a route', () => {
  const question = engagementById('discovery-or-guidance');
  expect(classifyEngagementAnswer(question!, 'Show me how it guides someone to the right place.')).toMatchObject({
    optionId: 'guidance',
    semanticCategory: 'VERIFIED_GUIDANCE',
  });
});

test('an unclassified answer grants no destination', () => {
  const question = engagementById('discovery-or-guidance');
  expect(classifyEngagementAnswer(question!, 'Tell me something unrelated.')).toBeNull();
});

test('the first governed identity stop asks the discovery-or-guidance question', () => {
  const firstStop = LANDING_TOUR_CHAPTERS[0].stops[0];
  expect(firstStop.id).toBe('stop-hero-meet');
  expect(firstStop.engagementQuestion?.id).toBe('discovery-or-guidance');
  expect(firstStop.engagementQuestion?.prompt).toContain('what Orb Weaver discovers');
});
