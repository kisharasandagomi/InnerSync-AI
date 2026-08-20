/**
 * Below-the-fold public content shown on the public welcome/sign-in screen.
 * Deliberately placed on `AuthPage`, not the post-login `LandingPage`: the
 * crisis-support directory below must be reachable by anyone who lands on
 * the site, not gated behind an account or behind the welcome screen's
 * Sign In / Create Account buttons (round 5 item 1) -- it is rendered
 * unconditionally regardless of `AuthPage`'s current mode. Static content
 * only, no ML/SHAP/explanation logic, and written to the same warm,
 * non-clinical, no-em-dash house style as the rest of the app (see
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

export interface DirectoryEntry {
  name: string;
  detail: string;
  lines: string[];
}

// Verbatim per the verified list supplied for this addition. Do not alter
// or add numbers here without re-verifying against the organisations'
// own published contact details. Article A (below) reads its two
// highlighted numbers directly from this same array rather than retyping
// them, specifically so the two copies can never drift apart. Exported
// (round 7) so SettingsPage's wellbeing signpost reads the same two
// entries the same way, rather than a third hand-typed copy of the numbers.
export const DIRECTORY: DirectoryEntry[] = [
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

// Looked up by name rather than fixed array index, so a future reordering
// of DIRECTORY can't silently point Article A's highlight box (or, round 7,
// the profile page's wellbeing signpost) at the wrong entry.
export const NIMH_ENTRY = DIRECTORY.find((e) => e.name.includes("NIMH"))!;
export const SUMITHRAYO_ENTRY = DIRECTORY.find((e) => e.name.startsWith("Sri Lanka Sumithrayo"))!;

/** Small abstract, icon-style illustrations for the three round-5 articles.
 *  Inline SVG (the same approach as MoodAvatar.tsx), navy/gold/off-white
 *  only, deliberately simple and non-representational -- no imagery that
 *  could evoke self-harm, distress, or anything clinical. */
function LifeRingIcon() {
  return (
    <svg viewBox="0 0 48 48" className="h-12 w-12 shrink-0" role="presentation" aria-hidden="true">
      <circle cx="24" cy="24" r="19" fill="none" stroke="#c99a2e" strokeWidth="6" />
      <circle cx="24" cy="24" r="19" fill="none" stroke="#14213d" strokeWidth="1" />
      <circle cx="24" cy="24" r="9" fill="#faf7f0" stroke="#14213d" strokeWidth="1.2" />
      {[0, 90, 180, 270].map((deg) => (
        <rect
          key={deg}
          x="22.5"
          y="3.5"
          width="3"
          height="7"
          fill="#faf7f0"
          transform={`rotate(${deg} 24 24)`}
        />
      ))}
    </svg>
  );
}

function ReachOutIcon() {
  return (
    <svg viewBox="0 0 48 48" className="h-12 w-12 shrink-0" role="presentation" aria-hidden="true">
      <path
        d="M8 14 h32 a3 3 0 0 1 3 3 v14 a3 3 0 0 1 -3 3 H20 l-8 7 v-7 h-4 a3 3 0 0 1 -3 -3 V17 a3 3 0 0 1 3 -3 Z"
        fill="#f4f1ea"
        stroke="#14213d"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      <circle cx="17" cy="24" r="1.8" fill="#c99a2e" />
      <circle cx="24" cy="24" r="1.8" fill="#c99a2e" />
      <circle cx="31" cy="24" r="1.8" fill="#c99a2e" />
    </svg>
  );
}

function GroundingIcon() {
  return (
    <svg viewBox="0 0 48 48" className="h-12 w-12 shrink-0" role="presentation" aria-hidden="true">
      <circle cx="24" cy="24" r="4" fill="#c99a2e" />
      <circle cx="24" cy="24" r="10" fill="none" stroke="#14213d" strokeWidth="1" opacity="0.6" />
      <circle cx="24" cy="24" r="16" fill="none" stroke="#14213d" strokeWidth="1" opacity="0.35" />
      <circle cx="24" cy="24" r="21" fill="none" stroke="#14213d" strokeWidth="1" opacity="0.2" />
    </svg>
  );
}

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

      {/* Round 5: three further articles, one per row (longer than the
          three-column set above, and Article A in particular needs the
          width). Article B's "professional support and treatment" is a
          deliberate, reviewed exception to the FORBIDDEN_CLINICAL_TERMS
          gate -- see the comment on that paragraph below and
          docs/research/methodology.md's "Static wellbeing article content"
          section for the full reasoning. */}
      <div className="mt-14 space-y-10">
        <article className="rounded-lg border border-line bg-card p-6">
          <div className="flex items-start gap-4">
            <LifeRingIcon />
            <div>
              <h2 className="text-base font-semibold tracking-tight text-ink">
                You are not alone, and help works
              </h2>
              <div className="mt-2 space-y-3">
                <p className="text-sm leading-relaxed text-ink-soft">
                  If things ever feel unbearable, please know this: reaching
                  out for help is one of the most common, and most
                  effective, things a person can do. It is not a sign of
                  weakness or failure. Every year, large numbers of students
                  and adults go through periods this hard, ask for support,
                  and come through the other side. There is nothing shameful
                  about needing help, and nothing unusual about it either.
                </p>
                <p className="text-sm leading-relaxed text-ink-soft">
                  It's true that Sri Lanka's suicide rate has historically
                  been higher than the global average. It stood at around 15
                  per 100,000 people in 2022 (WHO and national police data).
                  That figure matters less as a statistic than as context
                  for why services exist and are actively used: the rate has
                  fallen substantially since the 1990s, as awareness has
                  grown and support has become easier to reach. That trend
                  keeps moving in the right direction because people reach
                  out, and because it works.
                </p>
                <p className="text-sm leading-relaxed text-ink-soft">
                  The single most important thing to know is that most
                  people who reach out do get better. Talking to someone,
                  whether a friend, a family member, a counsellor, or a
                  helpline, genuinely changes how a crisis feels, usually
                  faster than it seems possible from the inside. You do not
                  have to already know what to say. You do not have to be in
                  a specific kind of crisis to call. You can call because
                  things feel too heavy, because you are scared of what
                  you're thinking, or just because you need to say it out
                  loud to another person.
                </p>
                <p className="text-sm leading-relaxed text-ink-soft">
                  If you need to talk to someone right now, these lines are
                  free or low-cost, and staffed by people who are ready to
                  listen:
                </p>
                {/* Sourced directly from DIRECTORY above, not retyped --
                    see that array's comment. */}
                <dl className="rounded-md border border-accent/50 bg-accent-soft/40 p-4">
                  {[NIMH_ENTRY, SUMITHRAYO_ENTRY].map((entry) => (
                    <div key={entry.name} className="mt-2 first:mt-0">
                      <dt className="text-sm font-semibold text-ink">{entry.name}</dt>
                      <dd className="text-sm leading-relaxed text-ink-soft">
                        {entry.lines.map((line, i) => (
                          <span key={i} className="block">
                            {line}
                          </span>
                        ))}
                      </dd>
                    </div>
                  ))}
                </dl>
                <p className="text-sm leading-relaxed text-ink-soft">
                  The full directory further down this page can help too,
                  whatever feels most reachable to you right now.
                </p>
                <p className="text-sm leading-relaxed text-ink-soft">
                  If things feel unbearable, reaching out is not giving up.
                  It is the strongest, most practical thing you can do for
                  yourself in that moment, and it's exactly what these
                  services are there for. Please call. You deserve support,
                  and it is genuinely available.
                </p>
              </div>
            </div>
          </div>
        </article>

        <article className="rounded-lg border border-line bg-card p-6">
          <div className="flex items-start gap-4">
            <ReachOutIcon />
            <div>
              <h2 className="text-base font-semibold tracking-tight text-ink">
                Common life stressors and getting support
              </h2>
              <div className="mt-2 space-y-3">
                <p className="text-sm leading-relaxed text-ink-soft">
                  Some of the hardest periods in a student's life don't come
                  from any one dramatic event. They come from ordinary
                  things that pile up: a relationship ending, an unresolved
                  conflict at home, worry about money, or an academic term
                  that has gone badly. Any one of these can be genuinely
                  painful. A few together, at once, can start to feel like
                  more than a person can carry.
                </p>
                <p className="text-sm leading-relaxed text-ink-soft">
                  It's easy to assume these kinds of stress are something
                  you should be able to manage alone, especially when none
                  of them look like an emergency from the outside. But pain
                  like this is real, and it's common.{" "}
                  {/* Deliberate, reviewed exception to the
                      FORBIDDEN_CLINICAL_TERMS gate: that list stops
                      InnerSync's own generated text from claiming to
                      diagnose or treat a student itself. This sentence does
                      the opposite -- it points a student toward real
                      external professional care, using the exact phrase
                      requested for round 5 -- so the concern the gate
                      exists for doesn't apply here. See
                      docs/research/methodology.md's "Static wellbeing
                      article content" section. */}
                  Professional support and treatment can genuinely help,
                  whether that's a university counsellor, a GP, or a
                  wellbeing service, and reaching out is not an overreaction,
                  even if things don't feel like a crisis yet.
                </p>
                <p className="text-sm leading-relaxed text-ink-soft">
                  One of the most consistent patterns in how people seek
                  support is that most wait too long, not too little.
                  Waiting for things to feel unmanageable before reaching
                  out often means going through more of the hard part alone
                  than necessary. You don't need to wait for a breaking
                  point. A conversation early, while things are merely
                  difficult, is often easier and more useful than one that
                  happens later.
                </p>
                <p className="text-sm leading-relaxed text-ink-soft">
                  This page isn't the place to work out exactly what you're
                  feeling, and neither is guessing on your own. If something
                  has felt heavy for a while, the most useful next step is
                  usually the simplest one: telling one person, whether
                  that's a friend, a tutor, or one of the services listed on
                  this page, honestly how things have been.
                </p>
              </div>
            </div>
          </div>
        </article>

        <article className="rounded-lg border border-line bg-card p-6">
          <div className="flex items-start gap-4">
            <GroundingIcon />
            <div>
              <h2 className="text-base font-semibold tracking-tight text-ink">
                Small things that help right now
              </h2>
              <div className="mt-2 space-y-3">
                <p className="text-sm leading-relaxed text-ink-soft">
                  When a thought or feeling gets loud and won't let go, you
                  don't need a big plan, just a way to shift your attention
                  for a few minutes. None of these fix the underlying
                  problem, but they can make the next hour easier, and
                  that's often enough to get through a hard moment.
                </p>
                <p className="text-sm leading-relaxed text-ink-soft">
                  Move your body, briefly. Stand up, stretch, walk to the
                  end of the corridor and back, or do twenty star jumps. It
                  sounds too simple to matter, but a short burst of movement
                  genuinely interrupts a spiralling thought better than
                  sitting still with it.
                </p>
                <p className="text-sm leading-relaxed text-ink-soft">
                  Call or message someone. It doesn't need to be a deep
                  conversation. Texting a friend about something completely
                  unrelated, or asking how their day is going, can pull your
                  attention somewhere else long enough to loosen a thought's
                  grip.
                </p>
                <p className="text-sm leading-relaxed text-ink-soft">
                  Step outside. Fresh air and a change of scenery, even for
                  two minutes, is a small, physical reset that sitting in
                  the same room rarely gives you.
                </p>
                <p className="text-sm leading-relaxed text-ink-soft">
                  Try naming five things. Look around and name five things
                  you can see, four things you can touch, three things you
                  can hear, two things you can smell, and one thing you can
                  taste. This simple exercise works by giving your attention
                  somewhere concrete to land, away from the thought that's
                  been circling.
                </p>
                <p className="text-sm leading-relaxed text-ink-soft">
                  None of these need to be done perfectly, and you don't
                  need to pick the "right" one. Whichever feels easiest to
                  start right now is the right one to try.
                </p>
              </div>
            </div>
          </div>
        </article>
      </div>

      <div className="mt-10 rounded-lg border border-accent/50 bg-accent-soft/40 p-6">
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
