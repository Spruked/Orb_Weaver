export type OrbStartupGreeting = {
  id: string;
  text: string;
};

export const ORB_STARTUP_GREETINGS: readonly OrbStartupGreeting[] = [
  {
    id: "wandered-into-my-web",
    text: `Well, look who wandered into my web.

I’m Weaver. I know this place from the buttons to the back rooms, and I can help you find what you need without making you dig through the whole site with a teaspoon.

You can speak to me, or click and tap me anytime.

I’m just waking up the machinery behind the curtain now. By the time I finish this sentence, we should both be ready.

So—what brought you here?`,
  },
  {
    id: "we-have-been-waiting",
    text: `There you are—we’ve been waiting for you.

I’m Weaver. I know this place inside and out—from the shiny buttons up front to the mysterious back rooms where the internet keeps its loose cables.

Tell me what you’re looking for, and I’ll help you find it without making you excavate the entire site with a teaspoon.

You can talk to me, click me, or tap me whenever you need help. Politely, ideally. I have standards now.

I’m just waking up the machinery behind the curtain. By the time you finish reading this sentence, everything should be humming, blinking, and pretending it was ready all along.

So, what brought you here?`,
  },
  {
    id: "entered-my-web",
    text: `Welcome. You have entered my web.

I am Weaver—keeper of the buttons, knower of the back rooms, and occasional negotiator with stubborn loading screens.

Speak, click, or tap, and I shall guide you to what you seek—without forcing you to wander through every page carrying nothing but hope and a teaspoon.

Behind the curtain, the machinery is stirring. Levers are lifting. Gears are turning. One dramatic light is blinking for no obvious reason.

And now, the stage is yours.

What are you looking for?`,
  },
  {
    id: "statistically-bound-to-happen",
    text: `You found me. Statistically, this was bound to happen eventually.

I’m Weaver. I know this site—from the obvious buttons to the obscure corners nobody visits unless something has gone terribly wrong.

Tell me what you need, and I’ll point you in the right direction without making you comb through the entire site like someone searching for a lost receipt.

You can talk to me, click me, or tap me at any time. Please avoid shaking the screen. It rarely helps.

I’m starting up the machinery behind the curtain now. By the end of this sentence, everything should be operational—or at least confidently pretending to be.

So, what brought you here?`,
  },
];

const SESSION_GREETING_KEY = "orbweaver-startup-greeting-id";
const LAST_GREETING_KEY = "orbweaver-last-startup-greeting-id";

const readStorage = (storage: Storage, key: string): string | null => {
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
};

const writeStorage = (storage: Storage, key: string, value: string): void => {
  try {
    storage.setItem(key, value);
  } catch {
    // Storage can be unavailable in hardened or private browser contexts.
  }
};

export function selectOrbStartupGreeting(random: () => number = Math.random): OrbStartupGreeting {
  if (typeof window === "undefined") return ORB_STARTUP_GREETINGS[0];

  const sessionGreetingId = readStorage(window.sessionStorage, SESSION_GREETING_KEY);
  const sessionGreeting = ORB_STARTUP_GREETINGS.find((greeting) => greeting.id === sessionGreetingId);
  if (sessionGreeting) return sessionGreeting;

  const lastGreetingId = readStorage(window.localStorage, LAST_GREETING_KEY);
  const eligible = ORB_STARTUP_GREETINGS.filter((greeting) => greeting.id !== lastGreetingId);
  const pool = eligible.length ? eligible : ORB_STARTUP_GREETINGS;
  const selected = pool[Math.min(pool.length - 1, Math.floor(random() * pool.length))];

  writeStorage(window.sessionStorage, SESSION_GREETING_KEY, selected.id);
  writeStorage(window.localStorage, LAST_GREETING_KEY, selected.id);
  return selected;
}
