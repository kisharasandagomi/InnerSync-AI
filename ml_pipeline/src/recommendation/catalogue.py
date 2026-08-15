"""Concrete first-step actions mapped to each of the 14 v2 features.

Only **raising** factors carry recommendations: a factor already working in the
student's favour needs acknowledging, not fixing.

Every action is written as a specific, small first step that a student could
complete this week — per `CLAUDE.md`, "never provide generic recommendations".
"Manage your stress better" is not an action; "book one 30-minute slot in a
library study room for tomorrow" is.

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
        category: Grouping used for later engagement analytics and for the
            Adaptive Recovery Framework (Component 5, not built yet).
        title: Short label for the suggestion.
        action: The specific first step. Must be completable in one week.
        rationale: Why this is being suggested, in plain language, phrased so it
            connects to what the student already read in their explanation.
    """

    category: str
    title: str
    action: str
    rationale: str


# One template per feature, keyed by feature name. Only the "raising" direction
# is represented — see module docstring.
RECOMMENDATION_CATALOGUE: dict[str, RecommendationTemplate] = {
    "self_esteem": RecommendationTemplate(
        category="self_reflection",
        title="A short weekly note on what went well",
        action=(
            "At the end of this week, write down three things you handled well "
            "— however small, including ordinary ones like getting to a 9am or "
            "replying to a message you had been putting off."
        ),
        rationale=(
            "When you are being hard on yourself, the things that went fine "
            "tend to stop registering. Writing them down makes them visible "
            "again."
        ),
    ),
    "mental_health_history": RecommendationTemplate(
        category="practical_support",
        title="Return to something that helped before",
        action=(
            "Think of one thing that genuinely helped when you last felt "
            "stretched — a person you spoke to, a routine, a service you used "
            "— and take the first step back toward it this week."
        ),
        rationale=(
            "You have navigated periods like this before, and what worked then "
            "is often still available to you now."
        ),
    ),
    "headache": RecommendationTemplate(
        category="physical",
        title="Break up long screen stretches",
        action=(
            "For the next three study sessions, stop every 45 minutes and look "
            "away from your screen for two minutes — standing up and refilling "
            "a glass of water is enough."
        ),
        rationale=(
            "Frequent head tension often tracks long unbroken periods of "
            "screen focus, and short interruptions ease it more reliably than "
            "pushing through."
        ),
    ),
    "breathing_problem": RecommendationTemplate(
        category="physical",
        title="A two-minute breathing reset",
        action=(
            "Once a day this week, sit down and breathe in for a count of "
            "four, hold for four, out for four, hold for four — repeat eight "
            "times. Set it to a fixed moment, such as just before you start "
            "studying."
        ),
        rationale=(
            "Slowing your breathing deliberately for a couple of minutes gives "
            "your body a clear signal to settle, and it is easiest to build "
            "when attached to something you already do daily."
        ),
    ),
    "noise_level": RecommendationTemplate(
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
    "living_conditions": RecommendationTemplate(
        category="environment",
        title="Change one thing about your main space",
        action=(
            "Pick the single thing about your room that irritates you most and "
            "change it this week — clearing the desk surface you work at, or "
            "moving where you charge your phone overnight."
        ),
        rationale=(
            "You cannot usually change your housing quickly, but one visible "
            "improvement in the space you spend most time in tends to shift how "
            "the whole room feels."
        ),
    ),
    "safety": RecommendationTemplate(
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
    "basic_needs": RecommendationTemplate(
        category="practical_support",
        title="Check what your university already offers",
        action=(
            "Look up your students' union or student services page for "
            "hardship support this week — most universities have a fund, a food "
            "pantry, or an adviser, and applying is usually a short form."
        ),
        rationale=(
            "When day-to-day essentials are uncertain, everything else gets "
            "harder. These services exist precisely for this and are commonly "
            "under-used."
        ),
    ),
    "academic_performance": RecommendationTemplate(
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
    "study_load": RecommendationTemplate(
        category="academic",
        title="Map your deadlines onto actual hours",
        action=(
            "Write out every deadline for the next three weeks, then block the "
            "hours you will spend on each into your calendar. If the hours do "
            "not fit, that is the point — take that to your personal tutor."
        ),
        rationale=(
            "A workload that feels impossible in the abstract is easier to deal "
            "with once it is visible, and an over-full calendar is concrete "
            "evidence to bring to a conversation about extensions."
        ),
    ),
    "teacher_student_relationship": RecommendationTemplate(
        category="academic",
        title="One low-stakes contact with teaching staff",
        action=(
            "Email one lecturer or your personal tutor this week with a single "
            "specific question about the course — not about how you are coping, "
            "just about the work."
        ),
        rationale=(
            "When contact with teaching staff feels strained, one short "
            "practical exchange is a lower-pressure way to reset it than "
            "waiting for a bigger conversation."
        ),
    ),
    "social_support": RecommendationTemplate(
        category="social",
        title="Reach one person directly",
        action=(
            "Message one person you have not spoken to properly in a few weeks "
            "and suggest something specific and short — a coffee between "
            "lectures, or a walk on a named day."
        ),
        rationale=(
            "Feeling unsupported rarely improves through general socialising. "
            "One direct, specific arrangement with one person does more than "
            "being around more people."
        ),
    ),
    "peer_pressure": RecommendationTemplate(
        category="social",
        title="Decline one thing this week",
        action=(
            "Identify one invitation or expectation this week that you would "
            "rather not take on, and say no to it plainly — no explanation "
            "required beyond that it does not work for you."
        ),
        rationale=(
            "Pressure from people around you builds when every request gets "
            "accepted. Practising one clear refusal on something low-stakes "
            "makes the next one easier."
        ),
    ),
    "extracurricular_activities": RecommendationTemplate(
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
}


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
