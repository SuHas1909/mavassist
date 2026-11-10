# Security scan (OWASP ZAP baseline)

**Run:** 2026-11-10, against the Docker stack (web app through nginx, and the API), with the scanner on the stack's
network and AI keys blank. Reports: `test-evidence-final-2026-11-10/zap/` (HTML, JSON, Markdown and logs).
The baseline scan is passive: it spiders the site and inspects responses; it does not attack forms.

| Target | High | Medium | Low | Informational |
|---|---|---|---|---|
| Web app, first scan | 0 | 1 | 5 | 2 |
| Web app, after the fix | 0 | 0 | 5 | 2 |
| API | 0 | 0 | 0 | 1 |

## Fixed

| Finding | Risk | Fix |
|---|---|---|
| CSP: Failure to Define Directive with No Fallback (10055) | Medium | `form-action` does not fall back to `default-src`, so forms could post anywhere. Added `form-action 'self'` to the Content-Security-Policy in `frontend/nginx.conf` (Docker) and `frontend/vercel.json` (cloud), then re-scanned: no medium findings remain. |

## Remaining low findings (documented, not changed)

| Finding | Why it is accepted for this release |
|---|---|
| Cross-Origin-Embedder-Policy header missing (90004) | The app does not use cross-origin isolation features (SharedArrayBuffer, high-resolution timers). `require-corp` would also block any future cross-origin image without adding protection the CSP does not already give. |
| Cross-Origin-Opener-Policy header missing (90004) | The app opens no cross-origin windows that need isolation; external office links open as normal navigation. Can be added as `same-origin` later with no expected impact. |
| Cross-Origin-Resource-Policy header missing (90004) | All assets are same-origin and the CSP already restricts loading to `'self'`. |
| Permissions Policy header not set (10063) | The app uses no camera, microphone, location or other powerful features, so there is nothing to restrict. |
| Server leaks version via the `Server` header (10036) | nginx reports its version on the local Docker demo. Low risk for a local demo; set `server_tokens off;` before any public deployment. |

Informational items (modern web application; storable / non-storable content) need no action.

## Related automated checks

* `Security / role` tests (`test_authentication_and_security`, `test_every_admin_route_denies_student`,
  `test_rate_limit_and_headers`): password hashing, token expiry and audience, every administrator route denied to a
  student, rate limiting and security headers.
* Not covered here: HTTPS on cloud staging (the demo runs on the local Docker stack; see `SCOPE_CHANGES.md`).
