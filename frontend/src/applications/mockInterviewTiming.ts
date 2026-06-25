// Timing constants for the text-mode mock-interview runner (M2). These mirror
// the voice-oriented spec faithfully, treating "begun typing" as "begun
// speaking". Max windows come from each question's `time_limit_seconds`
// (intro 300s, others 180s); the min windows and grace periods live here.

/** Seconds to wait for the candidate to *start* before escalating. */
export const GRACE_S = 5
/** Seconds of inactivity (after the min window) that auto-advances. */
export const INACTIVITY_ADVANCE_S = 5
/** Show the blinking red warning during the final N seconds before max. */
export const WARNING_S = 10
/** Minimum answer window for the intro question. */
export const MIN_INTRO_S = 60
/** Minimum answer window for every other question. */
export const MIN_OTHER_S = 15

/** The minimum answer window for a question, in seconds. */
export function minWindow(isIntro: boolean): number {
  return isIntro ? MIN_INTRO_S : MIN_OTHER_S
}
