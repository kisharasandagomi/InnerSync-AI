/**
 * Below-the-fold public content shown under the sign-in/register form
 * (round 4). Deliberately placed on `AuthPage`, not the post-login
 * `LandingPage`: the crisis-support directory below must be reachable by
 * anyone who lands on the site, not gated behind an account. Static
 * content only, no ML/SHAP/explanation logic, and written to the same
 * warm, non-clinical, no-em-dash house style as the rest of the app (see
 * `docs/research/methodology.md` § Style rule: no em-dashes).
 */

interface Article {
  title: string;
  paragraphs: string[];
}

const ARTICLES: Article[] = [
  {
    title: "Reducing everyday stress",
    paragraphs: [
      "Stress rarely arrives as one big thing. It tends to build from a stack of smaller ones: a deadline, a bad night's sleep, a message you've been meaning to answer. None of them look serious alone, which is part of why the total can catch you off guard.",
      "Small, specific actions tend to help more than big resolutions. Naming the one thing that's weighing on you most today, and doing something concrete about just that one thing, usually beats trying to fix everything at once.",
    ],
  },
  {
    title: "Balancing academic and personal life",
    paragraphs: [
      "University asks a lot of your time, and it's easy to let everything outside coursework quietly slide: friendships, hobbies, rest. The balance rarely fixes itself; it usually takes a deliberate, fairly small choice, like protecting one evening a week that isn't about work.",
      "It's also worth noticing when the balance has tipped for a while rather than just today. A single hard week is normal. A pattern of hard weeks is worth paying attention to and, where it helps, talking to someone about.",
    ],
  },
  {
    title: "Why early check-ins matter",
    paragraphs: [
      "It's easier to notice a pattern than a single bad day, and it's easier to act on stress early than once it's been building for months. Checking in regularly, even briefly, gives you and the people who support you something concrete to look back on.",
      "This isn't about catching a problem before it's allowed to exist. It's about having an honest, low-effort record of how things have actually been going, so a conversation with a tutor, a friend, or a wellbeing service can start from something real.",
    ],
  },
];

const STEPS: { title: string; body: string }[] = [
  {
    title: "Answer a short check-in",
    body: "A few plain questions about how the last week or two has felt, answered in chat or on a simple form, whichever you prefer.",
  },
  {
    title: "Get a plain-language read",
    body: "No scores or jargon. Just a short, honest paragraph about what seems to be going on, in language you'd use with a friend.",
  },
  {
    title: "See a few small suggestions",
    body: "One or two specific, doable next steps tied to what actually came up, not a generic list.",
  },
  {
    title: "Track how things shift",
    body: "Check in again whenever you like and see how things compare over time.",
  },
];

interface DirectoryEntry {
  name: string;
  detail: string;
  lines: string[];
}

// Verbatim per the verified list supplied for this addition. Do not alter
// or add numbers here without re-verifying against the organisations'
// own published contact details.
const DIRECTORY: DirectoryEntry[] = [
  {
    name: "National Mental Health Helpline (NIMH)",
    detail: "",
    lines: ["1926 (24/7, free, call or SMS)", "WhatsApp 075 555 1926"],
  },
  {
    name: "National Institute of Mental Health",
    detail: "Mulleriyawa New Town",
    lines: ["+94 11 257 8234-7"],
  },
  {
    name: "Sri Lanka Sumithrayo (emotional support / suicide prevention)",
    detail: "Colombo, 60B Horton Place",
    lines: ["+94 11 269 2909"],
  },
  {
    name: "Lanka Lifeline",
    detail: "",
    lines: ["1375"],
  },
  {
    name: "CCC Foundation",
    detail: "",
    lines: ["1333"],
  },
  {
    name: "Shanthi Maargam",
    detail: "",
    lines: ["0717 639 898"],
  },
];

export function HomeContent() {
  return (
    <div className="mx-auto mt-16 max-w-3xl">
      <div className="border-t border-line pt-12 text-center">
        <p className="text-lg font-medium leading-relaxed text-ink">
          Your wellbeing is not a side project. It matters on its own terms,
          not just as something to manage so you can keep studying.
        </p>
      </div>

      <div className="mt-14 grid gap-8 sm:grid-cols-3">
        {ARTICLES.map((article) => (
          <div key={article.title}>
            <h2 className="text-base font-semibold tracking-tight text-ink">
              {article.title}
            </h2>
            <div className="mt-2 space-y-3">
              {article.paragraphs.map((p, i) => (
                <p key={i} className="text-sm leading-relaxed text-ink-soft">
                  {p}
                </p>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-14 rounded-lg border border-line bg-card p-6">
        <h2 className="text-base font-semibold tracking-tight text-ink">
          How this works
        </h2>
        <ol className="mt-4 grid gap-5 sm:grid-cols-2">
          {STEPS.map((step, i) => (
            <li key={step.title} className="flex gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-ink">
                {i + 1}
              </span>
              <div>
                <p className="text-sm font-medium text-ink">{step.title}</p>
                <p className="mt-0.5 text-sm leading-relaxed text-ink-soft">
                  {step.body}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </div>

      <div className="mt-14 rounded-lg border border-accent/50 bg-accent-soft/40 p-6">
        <h2 className="text-base font-semibold tracking-tight text-ink">
          Sri Lanka mental health support directory
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-soft">
          If you or someone you know needs to talk to someone now, these
          services are free or low-cost to contact.
        </p>
        <dl className="mt-5 grid gap-5 sm:grid-cols-2">
          {DIRECTORY.map((entry) => (
            <div key={entry.name}>
              <dt className="text-sm font-semibold text-ink">{entry.name}</dt>
              <dd className="mt-1 text-sm leading-relaxed text-ink-soft">
                {entry.detail && <span className="block">{entry.detail}</span>}
                {entry.lines.map((line, i) => (
                  <span key={i} className="block">
                    {line}
                  </span>
                ))}
              </dd>
            </div>
          ))}
        </dl>
        <p className="mt-6 text-xs leading-relaxed text-ink-faint">
          These details were last verified in August 2026 and may change. We
          recommend checking each organisation's own page periodically rather
          than treating this list as permanently accurate.
        </p>
      </div>
    </div>
  );
}
