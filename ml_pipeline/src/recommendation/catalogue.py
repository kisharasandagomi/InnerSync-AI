"""Concrete first-step actions mapped to each of the 14 v2 features.

Only **raising** factors carry recommendations: a factor already working in the
student's favour needs acknowledging, not fixing.

Every action is written as a specific, small first step that a student could
complete this week — per `CLAUDE.md`, "never provide generic recommendations".
"Manage your stress better" is not an action; "book one 30-minute slot in a
library study room for tomorrow" is.

**Two templates per feature.** `RECOMMENDATION_CATALOGUE[feature]` is a list of
`[primary, alternate]`. The point-in-time engine (`engine.py`) always uses the
primary (`[0]`) — nothing about that behaviour changed. The alternate exists
for the Adaptive Recovery Framework
(`backend/app/services/adaptive_recovery.py`): when the same factor has been
the top driver across consecutive check-ins and the student reported not
engaging with it, the alternate is substituted so the student is not shown the
identical suggestion again. Each alternate uses a genuinely different
mechanism from its primary (e.g. asking someone else's perspective instead of
self-reflection), not a reworded copy of the same idea.

Coverage note against CLAUDE.md's four canonical examples:
  - "academic pressure -> study planner"        -> study_load, academic_performance
  - "relationship issues -> journaling/social"  -> social_support,
                                                   teacher_student_relationship,
                                                   peer_pressure
  - "poor sleep -> sleep hygiene plan"          -> NOT AVAILABLE. `sleep_quality`
        was excluded from the v2 model as a leaking feature (ADR-003), so the
        model cannot attribute stress to it and the engine cannot honestly
        recommend on it.
  - "physical inactivity -> walking/exercise"   -> NOT AVAILABLE. The dataset has
        no exercise or physical-activity field at all. `extracurricular_activities`
        measures commitment load, not activity, and is not a substitute.
Both gaps are properties of the dataset, not of this component, and are
recorded in `docs/research/methodology.md`.

No text here may contain clinical vocabulary or ML terminology; every string is
checked by `validate_user_facing_text()` before it reaches a student.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecommendationTemplate:
    """One actionable suggestion tied to a single contributing factor.

    Attributes:
        category: Grouping used for later engagement analytics and by the
            Adaptive Recovery Framework's logging.
        title: Short label for the suggestion.
        action: The specific first step. Must be completable in one week.
            Used whenever `hobby_action_template` is unset, or the student
            has no `hobby` set on their profile — the generic phrasing this
            template has always had.
        rationale: Why this is being suggested, in plain language, phrased so it
            connects to what the student already read in their explanation.
        hobby_action_template: An optional alternate `action`, containing
            exactly one `{hobby}` placeholder, used in place of `action`
            only when the student has set a `hobby` on their profile (see
            `backend/app/models/user_profile.py`). `None` for every template
            that isn't personalisable this way — round 3 added this to
            exactly one template (`mental_health_history`'s primary) rather
            than every entry; see that template for the reasoning. The
            interpolated string still passes through
            `validate_user_facing_text()` like any other user-facing text,
            with the plain `action` as the fallback if a student's own
            `hobby` text happens to trip the gate — see
            `engine.build_recommendation_plan`.
    """

    category: str
    title: str
    action: str
    rationale: str
    hobby_action_template: str | None = None


# feature -> [primary, alternate]. Both directions covered — see module docstring.
RECOMMENDATION_CATALOGUE: dict[str, list[RecommendationTemplate]] = {
    "self_esteem": [
        RecommendationTemplate(
            category="self_reflection",
            title="A short weekly note on what went well",
            action=(
                "At the end of this week, write down three things you handled well, "
                "however small, including ordinary ones like getting to a 9am or "
                "replying to a message you had been putting off."
            ),
            rationale=(
                "When you are being hard on yourself, the things that went fine "
                "tend to stop registering. Writing them down makes them visible "
                "again."
            ),
        ),
        RecommendationTemplate(
            category="self_reflection",
            title="Ask someone who knows you well",
            action=(
                "This week, ask one person who knows you well what they think "
                "you're good at, and actually listen to the answer rather than "
                "deflecting it."
            ),
            rationale=(
                "It's hard to see your own strengths clearly when you're being "
                "hard on yourself. Someone else's view can catch things you've "
                "stopped noticing."
            ),
        ),
    ],
    "mental_health_history": [
        RecommendationTemplate(
            category="practical_support",
            title="Return to something that helped before",
            action=(
                "Think of one thing that genuinely helped when you last felt "
                "stretched: a person you spoke to, a routine, a service you used. "
                "Take the first step back toward it this week."
            ),
            rationale=(
                "You have navigated periods like this before, and what worked then "
                "is often still available to you now."
            ),
            # Chosen for hobby personalisation because its own generic
            # phrasing is already about returning to a helpful routine — a
            # hobby is a direct, concrete example of that, not a stretch.
            # Falls back to the plain `action` above whenever no hobby is
            # set, or the interpolated text ever fails the safety gate.
            hobby_action_template=(
                "Think of one thing that genuinely helped when you last felt "
                "stretched (for you, that might be {hobby}) and take the first "
                "step back toward it this week."
            ),
        ),
        RecommendationTemplate(
            category="practical_support",
            title="Tell one person briefly what's going on",
            action=(
                "Pick one person you trust and tell them, in a sentence or two, "
                "that things have felt heavy lately. You don't need a plan, just "
                "to say it out loud to someone."
            ),
            rationale=(
                "Carrying this alone tends to make it feel heavier than it is. "
                "Saying it briefly to one person often loosens that, even without "
                "solving anything."
            ),
        ),
    ],
    "headache": [
        RecommendationTemplate(
            category="physical",
            title="Break up long screen stretches",
            action=(
                "For the next three study sessions, stop every 45 minutes and look "
                "away from your screen for two minutes. Standing up and refilling "
                "a glass of water is enough."
            ),
            rationale=(
                "Frequent head tension often tracks long unbroken periods of "
                "screen focus, and short interruptions ease it more reliably than "
                "pushing through."
            ),
        ),
        RecommendationTemplate(
            category="physical",
            title="Check the basics for one day",
            action=(
                "For one day, track three things: how much water you drink, how "
                "far you sit from your screen, and whether the room is well lit. "
                "Adjust whichever looks off."
            ),
            rationale=(
                "Headaches often trace back to a small physical cause rather than "
                "the workload itself. A one-day check is a quick way to rule the "
                "obvious ones out."
            ),
        ),
    ],
    "breathing_problem": [
        RecommendationTemplate(
            category="physical",
            title="A two-minute breathing reset",
            action=(
                "Once a day this week, sit down and breathe in for a count of "
                "four, hold for four, out for four, hold for four, then repeat eight "
                "times. Set it to a fixed moment, such as just before you start "
                "studying."
            ),
            rationale=(
                "Slowing your breathing deliberately for a couple of minutes gives "
                "your body a clear signal to settle, and it is easiest to build "
                "when attached to something you already do daily."
            ),
        ),
        RecommendationTemplate(
            category="physical",
            title="Get outside for a few minutes",
            action=(
                "Once today, step outside for five minutes: no phone, just "
                "walking or standing somewhere with open air."
            ),
            rationale=(
                "A short change of environment and fresh air can ease physical "
                "tightness in a different way than sitting still does."
            ),
        ),
    ],
    "noise_level": [
        RecommendationTemplate(
            category="environment",
            title="Secure one reliably quiet slot",
            action=(
                "Book a library study room or silent-zone desk for one specific "
                "two-hour slot this week, and use it for the work you find hardest "
                "to concentrate on."
            ),
            rationale=(
                "A noisy space costs more effort than it appears to. One protected "
                "quiet block is usually easier to arrange than making your usual "
                "space quieter."
            ),
        ),
        RecommendationTemplate(
            category="environment",
            title="Try blocking the noise out instead of moving",
            action=(
                "Before looking for a new place to study, try earplugs, "
                "headphones, or a white-noise track at your current spot for one "
                "session and see if that's enough."
            ),
            rationale=(
                "Relocating takes effort and isn't always possible. Blocking the "
                "noise where you already are is often a faster fix to test first."
            ),
        ),
    ],
    "living_conditions": [
        RecommendationTemplate(
            category="environment",
            title="Change one thing about your main space",
            action=(
                "Pick the single thing about your room that irritates you most and "
                "change it this week, clearing the desk surface you work at, or "
                "moving where you charge your phone overnight."
            ),
            rationale=(
                "You cannot usually change your housing quickly, but one visible "
                "improvement in the space you spend most time in tends to shift how "
                "the whole room feels."
            ),
        ),
        RecommendationTemplate(
            category="environment",
            title="Spend deliberate time somewhere else",
            action=(
                "Book out two or three hours this week in a different environment, "
                "such as a library, a café, or a friend's place, somewhere that isn't the "
                "space that's bothering you."
            ),
            rationale=(
                "If your main space is hard to change quickly, regularly stepping "
                "away from it for a while can take the edge off without needing to "
                "fix the space itself."
            ),
        ),
    ],
    "safety": [
        RecommendationTemplate(
            category="practical_support",
            title="Make your regular routes feel more predictable",
            action=(
                "For journeys you make after dark, check whether your university "
                "runs a campus safety walk or late transport service, and save the "
                "number in your phone before you next need it."
            ),
            rationale=(
                "Feeling uneasy about getting around takes up steady background "
                "attention. Having a concrete option saved in advance removes some "
                "of that."
            ),
        ),
        RecommendationTemplate(
            category="practical_support",
            title="Travel with someone for now",
            action=(
                "For the specific journeys that feel unsafe, arrange to go with a "
                "flatmate or friend this week rather than alone."
            ),
            rationale=(
                "Company changes how a route feels even when nothing else about it "
                "does. It's a quick, practical adjustment while anything "
                "longer-term gets sorted."
            ),
        ),
    ],
    "basic_needs": [
        RecommendationTemplate(
            category="practical_support",
            title="Check what your university already offers",
            action=(
                "Look up your students' union or student services page for "
                "hardship support this week. Most universities have a fund, a food "
                "pantry, or an adviser, and applying is usually a short form."
            ),
            rationale=(
                "When day-to-day essentials are uncertain, everything else gets "
                "harder. These services exist precisely for this and are commonly "
                "under-used."
            ),
        ),
        RecommendationTemplate(
            category="practical_support",
            title="Ask one specific person directly",
            action=(
                "Rather than searching a website, message your personal tutor or "
                "your students' union welfare officer directly this week and ask "
                "what support is available."
            ),
            rationale=(
                "A direct message to a real person often moves faster than working "
                "through a webpage alone, and they can point you straight to what "
                "applies to you."
            ),
        ),
    ],
    "academic_performance": [
        RecommendationTemplate(
            category="academic",
            title="Get specific feedback on one piece of work",
            action=(
                "Choose the one module you are least confident about and go to that "
                "lecturer's next office hour with a single prepared question about "
                "where you are losing marks."
            ),
            rationale=(
                "Worry about how you are doing academically is usually vaguer than "
                "the actual problem. One concrete piece of feedback narrows it to "
                "something you can act on."
            ),
        ),
        RecommendationTemplate(
            category="academic",
            title="Check your work against the marking criteria",
            action=(
                "Pull up the marking criteria or rubric for one upcoming piece of "
                "work and go through it line by line against what you've done so "
                "far."
            ),
            rationale=(
                "Worry about how you're doing is often vaguer than the actual gap. "
                "Lining your work up against the real criteria turns a feeling "
                "into something specific."
            ),
        ),
    ],
    "study_load": [
        RecommendationTemplate(
            category="academic",
            title="Map your deadlines onto actual hours",
            action=(
                "Write out every deadline for the next three weeks, then block the "
                "hours you will spend on each into your calendar. If the hours do "
                "not fit, that is the point: take that to your personal tutor."
            ),
            rationale=(
                "A workload that feels impossible in the abstract is easier to deal "
                "with once it is visible, and an over-full calendar is concrete "
                "evidence to bring to a conversation about extensions."
            ),
        ),
        RecommendationTemplate(
            category="academic",
            title="Cut one thing instead of rescheduling everything",
            action=(
                "Look at this week's list and pick one non-essential task or "
                "reading to drop entirely, rather than just moving everything "
                "later."
            ),
            rationale=(
                "Rearranging a full schedule often just delays the same pressure. "
                "Actually removing one thing changes how much you're carrying."
            ),
        ),
    ],
    "teacher_student_relationship": [
        RecommendationTemplate(
            category="academic",
            title="One low-stakes contact with teaching staff",
            action=(
                "Email one lecturer or your personal tutor this week with a single "
                "specific question about the course, not about how you are coping, "
                "just about the work."
            ),
            rationale=(
                "When contact with teaching staff feels strained, one short "
                "practical exchange is a lower-pressure way to reset it than "
                "waiting for a bigger conversation."
            ),
        ),
        RecommendationTemplate(
            category="academic",
            title="Go to their office hour in person",
            action=(
                "Instead of emailing, go to one lecturer's office hour this week "
                "and raise a specific question about the course in person."
            ),
            rationale=(
                "If written contact hasn't felt easy, a short in-person "
                "conversation can land differently and is often less effort than "
                "it seems beforehand."
            ),
        ),
    ],
    "social_support": [
        RecommendationTemplate(
            category="social",
            title="Reach one person directly",
            action=(
                "Message one person you have not spoken to properly in a few weeks "
                "and suggest something specific and short, such as a coffee between "
                "lectures, or a walk on a named day."
            ),
            rationale=(
                "Feeling unsupported rarely improves through general socialising. "
                "One direct, specific arrangement with one person does more than "
                "being around more people."
            ),
        ),
        RecommendationTemplate(
            category="social",
            title="Join one structured activity",
            action=(
                "Go to one university club, society, or group session this week: "
                "something with a set time and place, rather than something you "
                "have to organise yourself."
            ),
            rationale=(
                "When reaching out to one person feels hard, being somewhere with "
                "other people already there can be an easier way back into "
                "contact."
            ),
        ),
    ],
    "peer_pressure": [
        RecommendationTemplate(
            category="social",
            title="Decline one thing this week",
            action=(
                "Identify one invitation or expectation this week that you would "
                "rather not take on, and say no to it plainly. No explanation is "
                "required beyond that it does not work for you."
            ),
            rationale=(
                "Pressure from people around you builds when every request gets "
                "accepted. Practising one clear refusal on something low-stakes "
                "makes the next one easier."
            ),
        ),
        RecommendationTemplate(
            category="social",
            title="Prepare your answer before you're asked",
            action=(
                "Think of one request you expect this week and decide your answer "
                "in advance, in a specific sentence, so you're not deciding on the "
                "spot."
            ),
            rationale=(
                "Saying no is harder in the moment than ahead of time. Having the "
                "words ready makes it easier to actually say them."
            ),
        ),
    ],
    "extracurricular_activities": [
        RecommendationTemplate(
            category="academic",
            title="Pause one commitment for a fortnight",
            action=(
                "Pick the commitment outside your studies that you would miss "
                "least, and step back from it for two weeks. Tell whoever needs to "
                "know that it is a short pause, not leaving."
            ),
            rationale=(
                "Taking on a lot outside study is often genuinely worthwhile, which "
                "is exactly why it is hard to reduce. A time-limited pause is easier "
                "to commit to than a permanent decision."
            ),
        ),
        RecommendationTemplate(
            category="academic",
            title="Hand off one part of it",
            action=(
                "Instead of stepping back from a commitment entirely, pick one "
                "specific task within it and ask someone else to take it on this "
                "week."
            ),
            rationale=(
                "You don't always need to leave something to lighten it. Sharing "
                "one piece of the load can make the rest more manageable."
            ),
        ),
    ],
}


def get_alternate_template(feature: str) -> RecommendationTemplate:
    """Return the alternate (non-primary) template for a feature.

    Used only by the Adaptive Recovery Framework, when the primary suggestion
    for a factor has already been shown across consecutive check-ins without
    engagement.

    Args:
        feature: Feature name; must be a key of `RECOMMENDATION_CATALOGUE`.

    Returns:
        The feature's alternate `RecommendationTemplate`.

    Raises:
        KeyError: If `feature` is not in the catalogue.
    """
    return RECOMMENDATION_CATALOGUE[feature][1]


# Shown instead of recommendations when nothing meaningful is pushing the
# student's stress upward. See `engine.build_recommendation_plan`.
AFFIRMATION_BY_CLASS: dict[int, str] = {
    0: (
        "There is nothing here that looks like it needs changing right now. "
        "What is working seems to be genuinely working, so the most useful "
        "thing is simply to keep it going."
    ),
    1: (
        "Nothing stands out as needing to change right now. It may be worth "
        "keeping an eye on how the next couple of weeks go, and checking back "
        "in if things start to feel heavier."
    ),
    2: (
        "No single area stands out clearly enough to build a specific step "
        "around. Given how much you seem to be carrying, talking things through "
        "with your university wellbeing service is likely to be more useful "
        "than anything automated here."
    ),
}

# Shown by the Adaptive Recovery Framework when predicted stress has been at
# the highest severity level across 3+ consecutive check-ins, regardless of
# engagement — replaces the normal recommendation list rather than
# supplementing it. See `docs/governance/ethical_framework.md`'s escalation
# principle: "a clear, non-alarming prompt to contact university wellbeing
# services or a relevant crisis resource."
SUSTAINED_HIGH_STRESS_ESCALATION_MESSAGE = (
    "Your check-ins over the past few visits have consistently shown a lot of "
    "pressure, not just today. That's worth taking seriously, and it's beyond "
    "what automated suggestions can really help with. Please get in touch "
    "with your university wellbeing service this week. If things ever feel "
    "urgent, contact a crisis service or emergency care straight away."
)
