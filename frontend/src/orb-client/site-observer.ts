import type { OrbSiteSnapshot, OrbVisibleControl } from './types';

const CONTROL_SELECTOR = 'a[href],button,input,select,textarea,[role="button"],[role="link"],[data-orb-target]';

const clean = (value?: string | null, max = 160) => (value || '').replace(/\s+/g, ' ').trim().slice(0, max);

const visible = (element: HTMLElement) => {
  const rect = element.getBoundingClientRect();
  const style = window.getComputedStyle(element);
  return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
};

export function captureSiteSnapshot(): OrbSiteSnapshot {
  const controls: OrbVisibleControl[] = [];
  document.querySelectorAll<HTMLElement>(CONTROL_SELECTOR).forEach((element) => {
    if (controls.length >= 80 || !visible(element)) return;
    const href = element instanceof HTMLAnchorElement ? element.href : undefined;
    controls.push({
      tag: element.tagName.toLowerCase(),
      role: clean(element.getAttribute('role'), 40) || undefined,
      type: clean(element.getAttribute('type'), 40) || undefined,
      text: clean(element.getAttribute('aria-label') || element.textContent || element.getAttribute('placeholder')) || undefined,
      name: clean(element.getAttribute('name'), 80) || undefined,
      href: href ? clean(href, 500) : undefined,
    });
  });
  return {
    url: window.location.href,
    host: window.location.host,
    pathname: window.location.pathname || '/',
    title: clean(document.title, 300),
    viewport: { width: window.innerWidth, height: window.innerHeight },
    visible_controls: controls,
    captured_at: new Date().toISOString(),
  };
}

export function observeSite(onRoute: (snapshot: OrbSiteSnapshot) => void): () => void {
  let lastUrl = window.location.href;
  let timer = 0;
  const originalPushState = window.history.pushState;
  const originalReplaceState = window.history.replaceState;
  const check = () => {
    if (lastUrl === window.location.href) return;
    lastUrl = window.location.href;
    window.clearTimeout(timer);
    timer = window.setTimeout(() => onRoute(captureSiteSnapshot()), 80);
  };
  const pushStateWrapper: History['pushState'] = function (...args) {
    const result = originalPushState.apply(window.history, args);
    check();
    return result;
  };
  const replaceStateWrapper: History['replaceState'] = function (...args) {
    const result = originalReplaceState.apply(window.history, args);
    check();
    return result;
  };
  window.history.pushState = pushStateWrapper;
  window.history.replaceState = replaceStateWrapper;
  window.addEventListener('popstate', check);
  window.addEventListener('hashchange', check);
  const observer = new MutationObserver(check);
  observer.observe(document.documentElement, { childList: true, subtree: true });
  return () => {
    window.clearTimeout(timer);
    observer.disconnect();
    window.removeEventListener('popstate', check);
    window.removeEventListener('hashchange', check);
    if (window.history.pushState === pushStateWrapper) window.history.pushState = originalPushState;
    if (window.history.replaceState === replaceStateWrapper) window.history.replaceState = originalReplaceState;
  };
}
