export const LAYERS = [
  {
    name: "Kernel",
    id: "RAL",
    body: "WorldState, ActionProposal, Core-4, CycleEnvelope. Owns meaning and permission.",
  },
  {
    name: "Habitat",
    id: "Weaver / desktop ORB",
    body: "Where the organism lives. Snapshot of a site or window. Never the tribunal.",
  },
  {
    name: "Costume",
    id: "Skin Studio",
    body: "How approved primitives look and sound. Marketplace of implementations, not of rights.",
  },
  {
    name: "Body",
    id: "ROS adapter",
    body: "Physical effectors. Consumes authorized motion only.",
  },
  {
    name: "Nerves",
    id: "NATS or in-process bus",
    body: "Same envelope on every transport. Cmd/estop stay off disk.",
  },
] as const;

export const MOTION = [
  "idle_in_region",
  "focus_on",
  "approach",
  "point",
  "servo_orbit",
  "smooth_glide",
] as const;

export const SPEECH = ["speak", "whisper", "announce", "silent"] as const;

export const EXPRESSION = [
  "acknowledge",
  "listen",
  "think",
  "celebrate",
  "reassure",
  "confused",
] as const;

export const AGENCY_CONTRACT_VERSION = "tti.primitives.v1" as const;
