/**
 * ORB SKIN HASH UTILITY — shared
 * SHA-256 via Web Crypto API — works in Node 18+, browser, Tauri WebView2.
 */

export async function sha256Hex(data: ArrayBuffer | Uint8Array): Promise<string> {
  const buf = data instanceof Uint8Array ? data.buffer : data;
  const hash = await crypto.subtle.digest("SHA-256", buf);
  return toHex(hash);
}

export async function sha256HexFromString(text: string): Promise<string> {
  return sha256Hex(new TextEncoder().encode(text));
}

export function formatHash(hex: string): string {
  return hex.startsWith("sha256:") ? hex : `sha256:${hex}`;
}

export function stripHash(hash: string): string {
  return hash.startsWith("sha256:") ? hash.slice(7) : hash;
}

export function hashesMatch(a: string, b: string): boolean {
  return stripHash(a).toLowerCase() === stripHash(b).toLowerCase();
}

function toHex(buf: ArrayBuffer): string {
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
