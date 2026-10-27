# Frontend role-aware account-creation UI validation

**Execution date:** 2026-10-11  
**Validation type:** local static frontend checks; no browser/runtime session

## Change covered

The public gateway makes user-profile collection and creation administrative
operations. The frontend now mirrors that boundary:

- with authentication enabled, a regular USER does not render the Add New
  Account action or its modal;
- an ADMIN retains the action;
- when frontend authentication is explicitly disabled for local development,
  the existing demo-mode action remains available;
- the App-level create handler rejects a non-administrator invocation even if
  a caller bypasses the hidden button.

The frontend also maintains the authenticated session without extending the
server token lifetime: it refreshes a stored Keycloak refresh token when the
JWT expiry is within 10 seconds, shares concurrent refresh work, and retries a
request once after HTTP 401 only when refresh succeeds. Invalid refresh
responses clear the local session; transient refresh failures do not log or
expose token material.

The server-side gateway remains the enforcement point. This UI restriction
improves clarity and prevents a normal user from being offered an action that
would return HTTP 403.

## Files reviewed

- frontend/src/App.tsx
- frontend/src/components/Header.tsx
- frontend/src/services/auth.ts
- frontend/src/services/api.ts

## Commands and observed results

~~~powershell
Set-Location frontend
& 'C:\Program Files\nodejs\npm.cmd' run lint
& 'C:\Program Files\nodejs\npm.cmd' run build
~~~

**Observed:** lint passed and the Vite production build passed. The build
reported the pre-existing bundle-size advisory for a generated chunk larger
than 500 kB; it was a warning, not a build failure.

## Limitation

No current browser login, refresh-token exchange, or live gateway request was
run because Docker was not available. This confirms source behavior and
successful static build only; it does not replace a live USER-versus-ADMIN
browser acceptance test or a live refresh-token test.
