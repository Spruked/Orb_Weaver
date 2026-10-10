import type { Authorization, Task } from "./index";

const objectLike = (value: unknown): value is Record<string, unknown> => Boolean(value) && typeof value === "object";

export function parseTask(value: unknown): Task {
  if (!objectLike(value) || value.schema !== "web_tamp.task.v1" || typeof value.task_id !== "string" ||
      typeof value.objective !== "string" || typeof value.priority !== "number" ||
      value.priority < 0 || value.priority > 100 || typeof value.domain !== "string") {
    throw new Error("Invalid Web-TAMP Task contract");
  }
  return value as unknown as Task;
}

export function parseAuthorization(value: unknown): Authorization {
  if (!objectLike(value) || value.schema !== "web_tamp.authorization.v1" ||
      typeof value.authorization_id !== "string" || typeof value.proposal_id !== "string" ||
      typeof value.approval_id !== "string" || value.policy_decision !== "allowed" &&
      value.policy_decision !== "revoked" && value.policy_decision !== "expired") {
    throw new Error("Invalid Web-TAMP Authorization contract");
  }
  return value as unknown as Authorization;
}
