import { loginHandoffPath } from './AuthPage';

declare const describe: (name: string, suite: () => void) => void;
declare const test: (name: string, run: () => void | Promise<void>) => void;
declare const expect: any;

describe('existing-account login handoff', () => {
  test('returns a normal login to Weaver landing so the intro can run', () => {
    expect(loginHandoffPath('')).toBe('/');
  });

  test('keeps an explicit internal destination instead of overriding it', () => {
    expect(loginHandoffPath('?next=%2Fdashboard')).toBe('/dashboard');
  });

  test('rejects external redirect targets', () => {
    expect(loginHandoffPath('?next=https%3A%2F%2Fevil.example')).toBe('/');
  });
});
