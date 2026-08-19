import { HomeContent } from "../components/HomeContent";

/**
 * Round 6: the same articles/how-it-works/crisis directory shown on the
 * public sign-in page, reachable without signing out. Deliberately renders
 * `HomeContent` itself rather than a copy of its text -- see that
 * component's docstring for why the crisis directory content in particular
 * must never exist as two independently-editable copies.
 */
export function ResourcesPage() {
  return (
    <div>
      <p className="text-xs uppercase tracking-wider text-ink-faint">Resources</p>
      <h1 className="mt-2 text-xl font-semibold tracking-tight text-ink">
        Articles and support
      </h1>
      <p className="mt-3 text-base leading-relaxed text-ink-soft">
        The same guidance and crisis support directory shown on the sign-in
        page, so you don't have to sign out to find it again.
      </p>
      <HomeContent />
    </div>
  );
}
