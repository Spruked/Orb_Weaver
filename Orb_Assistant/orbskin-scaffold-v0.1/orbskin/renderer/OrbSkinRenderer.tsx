/**
 * ORB SKIN RENDERER — React
 * Runs identically in Electron (Chromium), Tauri (WebView2), and browser.
 * Reads from SkinContext — never touches the filesystem or IPC directly.
 *
 * Drop this into your existing ORB visual component tree.
 * Wrap your ORB root with <SkinProvider> and this will pick up any active skin.
 */

import { useEffect, useRef } from "react";
import { useSkinAssets, useSkinTokens } from "./useSkinAssets.js";

// ─────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────

interface OrbSkinRendererProps {
  /** Which element to render the skin onto — defaults to a div */
  as?: "div" | "canvas";
  className?: string;
  style?: React.CSSProperties;
  /** Called when skin finishes applying */
  onSkinApplied?: (skinId: string) => void;
}

// ─────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────

export function OrbSkinRenderer({
  as: Tag = "div",
  className,
  style,
  onSkinApplied,
}: OrbSkinRendererProps) {
  const assets = useSkinAssets();
  const tokens = useSkinTokens();
  const containerRef = useRef<HTMLDivElement | HTMLCanvasElement>(null);

  // Apply theme tokens to the container as CSS custom properties
  useEffect(() => {
    const el = containerRef.current;
    if (!el || !tokens) return;
    Object.entries(tokens).forEach(([key, value]) => {
      // token key convention: orb_primary_color → --orb-primary-color
      const cssVar = `--${key.replace(/_/g, "-")}`;
      el.style.setProperty(cssVar, value);
    });
  }, [tokens]);

  // Notify parent when skin changes
  useEffect(() => {
    if (assets?.skin_id) {
      onSkinApplied?.(assets.skin_id);
    }
  }, [assets?.skin_id, onSkinApplied]);

  if (!assets) {
    // No skin loaded — render nothing (ORB uses its default appearance)
    return null;
  }

  return (
    // @ts-expect-error — ref type union
    <Tag
      ref={containerRef}
      className={className}
      data-skin-id={assets.skin_id}
      style={{
        // Inline the CSS token values as a fallback for renderers
        // that don't support CSS custom properties natively
        ...buildInlineStyles(tokens),
        ...style,
      }}
    >
      {/* Body asset — PNG or GLB placeholder */}
      <OrbBodyAsset url={assets.urls.body_asset} />

      {/* Docked icon — shown when ORB is collapsed */}
      <OrbDockedIcon url={assets.urls.docked_icon} skinId={assets.skin_id} />

      {/* Particle overlay — optional */}
      {assets.urls.particle_profile && (
        <OrbParticleLayer profileUrl={assets.urls.particle_profile} />
      )}
    </Tag>
  );
}

// ─────────────────────────────────────────────
// SUB-COMPONENTS  (stubs — wire to your ORB visuals)
// ─────────────────────────────────────────────

function OrbBodyAsset({ url }: { url: string }) {
  const isGlb = url.toLowerCase().endsWith(".glb");

  if (isGlb) {
    // TODO: wire to your Three.js / Babylon loader
    // For now, a placeholder div signals that a 3D asset is available
    return (
      <div
        data-orb-body="glb"
        data-src={url}
        style={{ width: "100%", height: "100%", position: "absolute", inset: 0 }}
      />
    );
  }

  return (
    <img
      src={url}
      alt="ORB body"
      data-orb-body="png"
      style={{ width: "100%", height: "100%", objectFit: "contain", position: "absolute", inset: 0 }}
    />
  );
}

function OrbDockedIcon({ url, skinId }: { url: string; skinId: string }) {
  return (
    <img
      src={url}
      alt={`${skinId} docked icon`}
      data-orb-docked-icon
      style={{ display: "none" }} // ORB host shows/hides this based on dock state
    />
  );
}

function OrbParticleLayer({ profileUrl }: { profileUrl: string }) {
  // TODO: wire to your particle engine
  // Profile JSON tells the engine what to render
  return (
    <div
      data-orb-particles
      data-profile={profileUrl}
      style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
    />
  );
}

// ─────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────

function buildInlineStyles(tokens: Record<string, string>): React.CSSProperties {
  // Not all tokens map 1:1 to inline styles — just pass through as CSS vars
  // The actual style application is done via setProperty in the useEffect above
  return {};
}
