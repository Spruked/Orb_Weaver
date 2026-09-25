import { observedUseCasePointerRecords, USE_CASE_POINTER_TITLES } from './siteAuthoredUseCasePointers';
import { validateOrbPointerTarget } from './targetValidation';

afterEach(() => {
  document.body.innerHTML = '';
  window.history.replaceState({}, '', '/');
});

test('all eight authored use cases resolve only against exact live headings', () => {
  window.history.replaceState({}, '', '/use-cases');
  document.body.innerHTML = USE_CASE_POINTER_TITLES.map((title, index) =>
    `<article data-orb-target="use-case-${index + 1}"><h3>${title}</h3></article>`,
  ).join('');
  document.querySelectorAll('h3').forEach((heading) => {
    heading.getBoundingClientRect = () => ({
      left: 300, top: 250, right: 500, bottom: 290,
      x: 300, y: 250, width: 200, height: 40, toJSON: () => ({}),
    } as DOMRect);
  });

  const records = observedUseCasePointerRecords();
  expect(records.map((record) => record.target_id)).toEqual(
    Array.from({ length: 8 }, (_, index) => `use-case-${index + 1}`),
  );
  records.forEach((record) => {
    expect(record.runtime_policy?.may_point).toBe(true);
    expect(record.runtime_policy?.may_click).toBe(false);
    expect(validateOrbPointerTarget(record).ok).toBe(true);
  });

  document.querySelector('[data-orb-target="use-case-4"] h3')!.textContent = 'Unknown topic';
  expect(observedUseCasePointerRecords().map((record) => record.target_id)).not.toContain('use-case-4');
  window.history.replaceState({}, '', '/features');
  expect(observedUseCasePointerRecords()).toEqual([]);
});
