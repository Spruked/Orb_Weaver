const RETURN_TO_LOGIN_STORAGE_KEY = 'orbweaver-return-to-login-opt-in-v1';

export const returningAccountShortcutEnabled = (): boolean => {
  if (typeof window === 'undefined') return false;
  try {
    return window.localStorage.getItem(RETURN_TO_LOGIN_STORAGE_KEY) === '1';
  } catch {
    return false;
  }
};

export const setReturningAccountShortcut = (enabled: boolean): void => {
  if (typeof window === 'undefined') return;
  try {
    if (enabled) {
      window.localStorage.setItem(RETURN_TO_LOGIN_STORAGE_KEY, '1');
    } else {
      window.localStorage.removeItem(RETURN_TO_LOGIN_STORAGE_KEY);
    }
  } catch {
    // Preference storage must never block authentication.
  }
};

export const RETURN_TO_LOGIN_DISCLOSURE =
  'Remember this device so Orb Weaver can send you straight to Login after the opening splash. This first-party preference is used only for that shortcut. It does not sign you in, store your password, or identify you to other sites.';
