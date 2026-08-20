export type DockStatus = "unconfigured" | "available" | "unavailable" | "blocked";

export async function callDockAdapter(
  apiBase: string,
  action: string,
  argumentsPayload: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const response = await fetch(`${apiBase}/orb/dock/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, arguments: argumentsPayload }),
  });
  if (!response.ok) {
    return { status: "unavailable", message: `Dock adapter failed: ${response.status}` };
  }
  return response.json();
}

