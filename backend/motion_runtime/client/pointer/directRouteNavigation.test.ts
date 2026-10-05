import { describe, expect, test } from '@jest/globals';
import { resolveDirectRouteNavigation } from './directRouteNavigation';

describe('direct route navigation', () => {
  test('authorizes an explicit request for the navigation page', () => {
    expect(resolveDirectRouteNavigation('Take me to the navigation page')).toMatchObject({
      route: '/lidar-guidance', pointerTargetId: 'tour-lidar-guidance',
    });
  });

  test('does not treat a general question as a cross-page command', () => {
    expect(resolveDirectRouteNavigation('How does visual navigation work?')).toBeNull();
  });
});
