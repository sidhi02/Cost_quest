# Security notes for Cost Quest

## Included controls

- Passwords are stored using Werkzeug's scrypt password hash (`scrypt:32768:8:1`); plaintext passwords are not persisted.
- Registration and login enforce 12–128 character passwords, generic login failure messages, CSRF tokens, and database-backed attempt limits per IP and IP/email pair.
- Login rotates the signed Flask session and marks it permanent with a 12-hour lifetime.
- Production requires a 32-character-or-longer `SECRET_KEY`; debug mode and CSRF disablement are rejected in production.
- Production uses a `__Host-` session cookie with Secure, HttpOnly, SameSite=Lax, Path=/ and no Domain attribute.
- Watchlist reads and writes are scoped to the authenticated user ID.
- External feed endpoints must use HTTPS, cannot redirect, and reject local/private literal hosts.
- Search endpoints are rate-limited; provider errors are sanitized before display.
- Security headers include CSP, frame restrictions, no-referrer, content-type protection and a restrictive Permissions-Policy.

## Not included; required before a public multi-user launch

- Email ownership verification.
- Password reset and account recovery.
- MFA or passkeys.
- Account deletion and self-service personal-data export.
- Formal privacy notice, retention schedule and incident-response procedure.
- Independent penetration test and dependency vulnerability review.

There is no password-reset API in this release. Do not advertise account recovery until a secure, expiring, single-use token flow and email delivery provider have been implemented and tested.

## Production deployment requirements

1. Set `ENVIRONMENT=production` and generate a unique random `SECRET_KEY` of at least 32 characters, for example with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
2. Terminate TLS at a trusted reverse proxy/load balancer and ensure the application is reachable only through that proxy. Do not trust arbitrary forwarded headers.
3. Keep `CSRF_ENABLED=1`; production startup rejects disabling it.
4. Use a persistent, access-controlled database volume and encrypted backups. SQLite is intended for a single application instance; use PostgreSQL before horizontal scaling.
5. Store all provider credentials in the hosting platform's secret manager, never in Git or a client-side bundle.
6. Review provider terms for product data, images, caching, attribution and affiliate links before launch.
7. Run the complete CI suite, dependency audit, security test and live provider checks on the deployment target.

## Reporting

Do not put secrets, session cookies, database files or personal data in issue reports. Revoke and rotate any credential that may have been committed or exposed.
