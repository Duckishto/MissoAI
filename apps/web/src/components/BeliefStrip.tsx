/**
 * The system's current estimate for one concept.
 *
 * Deliberately not a progress bar. A single filled bar would claim a
 * precision the model does not have. The marker is the mean, the pale band
 * around it is the spread, and a wide band is the honest picture after one
 * or two answers. With no observations at all it says so in words rather
 * than drawing a bar at zero, which would read as failure instead of silence.
 */
export function BeliefStrip({
  concept,
  mean,
  variance,
  observations,
}: {
  concept: string;
  mean: number;
  variance: number;
  observations: number;
}) {
  const spread = Math.min(0.5, Math.sqrt(Math.max(variance, 0)));
  const left = Math.max(0, mean - spread) * 100;
  const width = Math.min(1, mean + spread) * 100 - left;

  return (
    <div className="py-3">
      <div className="flex items-baseline justify-between gap-4">
        <span className="text-sm font-medium text-ink">{concept}</span>
        <span className="text-xs text-ink-3">
          {observations === 0
            ? "no evidence yet"
            : `${observations} ${observations === 1 ? "response" : "responses"}`}
        </span>
      </div>

      {observations === 0 ? (
        <p className="mt-1.5 text-sm text-ink-2">
          Nothing has been observed for this concept, so there is no estimate to show.
        </p>
      ) : (
        <div
          className="relative mt-2 h-2 rounded-full"
          style={{ background: "var(--rule)" }}
          role="img"
          aria-label={`Estimated mastery ${(mean * 100).toFixed(0)} percent, plus or minus ${(spread * 100).toFixed(0)}`}
        >
          <div
            className="absolute inset-y-0 rounded-full"
            style={{ left: `${left}%`, width: `${width}%`, background: "var(--inferred-soft)" }}
          />
          <div
            className="absolute top-1/2 h-3 w-[3px] -translate-y-1/2 rounded-sm"
            style={{ left: `${mean * 100}%`, background: "var(--inferred)" }}
          />
        </div>
      )}
    </div>
  );
}
