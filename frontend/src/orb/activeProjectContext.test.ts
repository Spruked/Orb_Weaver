import {
  buildCustomerPageCapsuleUrl,
  canonicalOrbBaseUrl,
  getActiveOrbProjectContext,
  setActiveOrbProjectContext,
} from './activeProjectContext';

declare const describe: (name: string, suite: () => void) => void;
declare const beforeEach: (setup: () => void) => void;
declare const it: (name: string, test: () => void) => void;
declare const expect: any;

describe('active ORB project context', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState(null, '', '/welcome');
  });

  it('stores project 9 and builds campaign page-capsule URLs on localhost', () => {
    const stored = setActiveOrbProjectContext({
      project_id: '9',
      canonical_domain: 'campaign.orbweaver.spruked.com',
      canonical_base_url: canonicalOrbBaseUrl('campaign.orbweaver.spruked.com'),
      selected_crawl_job_id: '38',
      active_customer_route: '/investor',
    });

    expect(stored?.canonical_domain).toBe('campaign.orbweaver.spruked.com');
    expect(getActiveOrbProjectContext()?.selected_crawl_job_id).toBe('38');
    expect(buildCustomerPageCapsuleUrl(getActiveOrbProjectContext())).toBe('https://campaign.orbweaver.spruked.com/investor');
  });
});
