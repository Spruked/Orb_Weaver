import {
  api,
  type WebsiteOrbPointerMap,
  type WebsiteOrbPointerRecord,
} from "../services/api";

type LiveRuntimePolicy = {
  behavior: string;
  may_point: true;
  must_verify_before_action: boolean;
  requires_confirmation: boolean;
};

type LivePointerRecord = WebsiteOrbPointerRecord & {
  runtime_policy: LiveRuntimePolicy;
  source: "live_explicit_target";
};

let installed = false;
let observer: MutationObserver | null = null;
let activeRecords: WebsiteOrbPointerRecord[] | null = null;
let serverRecords: WebsiteOrbPointerRecord[] = [];

const normalize = (value: string): string =>
  (value || "").replace(/\s+/g, " ").trim();

const cssEscape = (value: string): string => {
  if (typeof CSS !== "undefined" && typeof CSS.escape === "function") {
    return CSS.escape(value);
  }
  return value.replace(/["\\]/g, "\\$&");
};

const targetLabel = (element: HTMLElement): string =>
  normalize(
    element.getAttribute("data-orb-meaning") ||
      element.getAttribute("aria-label") ||
      element.getAttribute("placeholder") ||
      element.textContent ||
      element.getAttribute("data-orb-target") ||
      "Website control",
  );

const aliasesFor = (element: HTMLElement, targetId: string, label: string): string[] => {
  const declared = (element.getAttribute("data-orb-aliases") || "")
    .split("|")
    .map(normalize)
    .filter(Boolean);
  const targetWords = targetId.replace(/[-_]+/g, " ");
  return Array.from(new Set([
    label,
    targetWords,
    `show me ${label}`,
    `where is ${label}`,
    `go to ${label}`,
    ...declared,
  ].filter((value) => value.length >= 2))).slice(0, 10);
};

const setTarget = (element: Element | null, targetId: string, aliases?: string): void => {
  if (!(element instanceof HTMLElement)) return;
  if (!element.getAttribute("data-orb-target")) {
    element.setAttribute("data-orb-target", targetId);
  }
  if (aliases && !element.getAttribute("data-orb-aliases")) {
    element.setAttribute("data-orb-aliases", aliases);
  }
};

/**
 * Orb Weaver's own application has a few critical controls that predate the
 * explicit target attribute. Mark only exact, deterministic selectors. This
 * never broad-matches arbitrary text and never clicks or submits anything.
 */
export const markKnownOrbWeaverTargets = (): void => {
  const route = window.location.pathname;
  if (route === "/preflight") {
    setTarget(
      document.querySelector('input[aria-label="Website URL"]'),
      "preflight-website-url",
      "website url|enter my website|where do i enter my website",
    );
    setTarget(
      document.querySelector('form button[type="submit"]'),
      "run-preflight",
      "run preflight|start preflight|scan this website",
    );
    setTarget(
      document.querySelector('a[href="/marketplace/products/basic-visitor-orb"]'),
      "explore-basic-orb",
      "basic orb|basic visitor orb",
    );
    setTarget(
      document.querySelector('a[href="/marketplace"]'),
      "view-orb-options",
      "orb options|packages|marketplace",
    );
  }
};

export const collectLivePointerRecords = (): LivePointerRecord[] => {
  markKnownOrbWeaverTargets();
  const route = window.location.pathname.replace(/\/+$/, "") || "/";
  const seen = new Set<string>();
  const records: LivePointerRecord[] = [];

  document.querySelectorAll<HTMLElement>("[data-orb-target]").forEach((element) => {
    const targetId = normalize(element.getAttribute("data-orb-target") || "");
    if (!targetId || seen.has(targetId)) return;
    seen.add(targetId);

    const label = targetLabel(element);
    const aliases = aliasesFor(element, targetId, label);
    records.push({
      target_id: targetId,
      page_route: route,
      target_type: ["INPUT", "TEXTAREA", "SELECT"].includes(element.tagName)
        ? "form_field"
        : element.tagName === "A"
          ? "nav"
          : "button",
      meaning: `${element.tagName.toLowerCase()}: ${label}`,
      intent_aliases: aliases,
      direct_aliases: aliases,
      topic_aliases: aliases,
      content_fingerprint: `live:${targetId}:${label.toLowerCase()}`,
      semantic_locator: `[data-orb-target="${cssEscape(targetId)}"]`,
      structural_context: { tag: element.tagName.toLowerCase() },
      confidence: 1,
      confidence_class: "VERIFIED",
      finding_class: "CONFIRMED",
      finding_subreason: "explicit_live_dom_target",
      pointer_health: "VERIFIED",
      runtime_policy: {
        behavior: "guide_or_act_within_permission_policy",
        may_point: true,
        must_verify_before_action: false,
        requires_confirmation: false,
      },
      source: "live_explicit_target",
    });
  });

  return records;
};

const refreshActiveRecords = (): void => {
  if (!activeRecords) return;
  const liveRecords = collectLivePointerRecords();
  const liveIds = new Set(liveRecords.map((record) => record.target_id));
  const retainedServerRecords = serverRecords.filter((record) => !liveIds.has(record.target_id));
  activeRecords.splice(0, activeRecords.length, ...retainedServerRecords, ...liveRecords);
};

const fallbackMap = (): WebsiteOrbPointerMap => ({
  schema: "orb_weaver.pointer_plot_map.live_fallback.v1",
  generated_at: new Date().toISOString(),
  record_count: 0,
  records: [],
  by_page: {},
  quality: { source: "explicit_live_dom_targets" },
  recovery: {},
});

/**
 * Installs one narrow adapter around the pointer-map request. Scan/Vault data
 * stays authoritative when available. Explicit live DOM targets are merged in
 * as a fail-closed runtime fallback so Weaver can always point to controls the
 * application itself has deliberately marked.
 */
export const installLocalPointerFallbacks = (): void => {
  if (installed) return;
  installed = true;

  const originalPointerMap = api.websiteOrbPointerMap.bind(api);
  api.websiteOrbPointerMap = async (domain?: string, signal?: AbortSignal) => {
    let pointerMap: WebsiteOrbPointerMap;
    try {
      pointerMap = await originalPointerMap(domain, signal);
    } catch {
      pointerMap = fallbackMap();
    }

    serverRecords = Array.isArray(pointerMap.records) ? [...pointerMap.records] : [];
    activeRecords = [...serverRecords];
    refreshActiveRecords();

    if (!observer) {
      observer = new MutationObserver(() => refreshActiveRecords());
      observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["data-orb-target", "data-orb-aliases", "aria-label", "placeholder"],
      });
      window.addEventListener("popstate", refreshActiveRecords);
      window.addEventListener("hashchange", refreshActiveRecords);
    }

    return {
      ...pointerMap,
      records: activeRecords,
      record_count: activeRecords.length,
      by_page: activeRecords.reduce<Record<string, string[]>>((pages, record) => {
        (pages[record.page_route] ||= []).push(record.target_id);
        return pages;
      }, {}),
    };
  };
};
