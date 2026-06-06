/**
 * Turn a FastAPI error response `detail` into a readable, user-facing string.
 *
 * FastAPI returns `detail` as either:
 *   - a plain string (HTTPException), or
 *   - an array of validation-error objects (RequestValidationError), e.g.
 *     [{ loc: ["body","topic"], msg: "String should have at most 1000 characters" }]
 * Throwing `new Error(detailArray)` would stringify to "[object Object]", so we
 * normalize both shapes here.
 */
export function formatApiError(detail: any, fallback = 'Request failed'): string {
  if (!detail) return fallback;
  if (typeof detail === 'string') return detail;

  if (Array.isArray(detail)) {
    const msgs = detail.map((e: any) => {
      const field = Array.isArray(e?.loc) ? e.loc[e.loc.length - 1] : '';
      const msg = e?.msg || 'invalid value';
      return field ? `${field}: ${msg}` : msg;
    });
    return msgs.join(' · ') || fallback;
  }

  if (detail?.msg) return detail.msg;
  try { return JSON.stringify(detail); } catch { return fallback; }
}

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

