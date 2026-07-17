/**
 * The design system, lifted from docs/design/direction-d.html.
 *
 * That file is the spec, not a reference. Four attempts at describing this direction in
 * prose produced four UIs the human rejected; the mockup ended the argument. So these are
 * its literal values, not an interpretation of them. If the film and the product ever
 * disagree on a colour, the mockup is right and this file is wrong.
 */

export const C = {
  bg: '#0B0C0E',
  panel: '#131519',
  sunk: '#0E1013',
  line: '#252930',
  ink: '#EDEFF2',
  dim: '#9BA3AF',
  faint: '#6B7280',
  pass: '#3DD68C',
  fail: '#FF6B6B',
  passBg: 'rgba(61,214,140,.10)',
  failBg: 'rgba(255,107,107,.10)',
  delInk: '#FFD9D9',
  addInk: '#D2F7E4',
} as const;

export const F = {
  mono: 'ui-monospace, "SF Mono", "Cascadia Code", Menlo, Consolas, monospace',
  sans: 'system-ui, -apple-system, "Segoe UI", sans-serif',
} as const;

/**
 * Two scales, because the film has two jobs and they do not want the same number.
 *
 * The first cut used one constant, 1.6, meant to map the 1020px mockup onto a 1920 frame.
 * It was wrong twice. 1920/1020 is 1.88, so it was 15% under on its own terms. And the
 * premise was wrong: matching the product's relative weight is right for a surface that
 * says "this is the product", and useless for text the film speaks in its own voice. That
 * text is read in a browser window, maybe at 360p, maybe on a phone, by someone scrubbing.
 * An 11.5px kicker rendered at 18px — 1.7% of frame height, gone at 360p — and the
 * prior-art line that carries the film's credibility rendered at 20px.
 *
 * UI keeps fidelity to the product. TYPE is the film talking. Nothing the film says lands
 * under 28px.
 */
export const UI = 1.88;
export const TYPE = 2.6;

/** Product-fidelity sizing: diff rows, terminals, anything quoting the real UI. */
export const px = (n: number) => n * UI;

/** The film's own voice: kickers, headlines, body. Floors at 28px. */
export const tx = (n: number) => Math.max(28, n * TYPE);

/**
 * Ligatures off, everywhere, forever. A font once rendered `>=` as `≥` in a tool whose
 * entire subject is the difference between `>=` and `>`. The HTML was correct and the font
 * was lying. It cost an afternoon to find.
 */
export const NO_LIGATURES = {
  fontVariantLigatures: 'none',
  fontFeatureSettings: '"liga" 0, "calt" 0',
} as const;
