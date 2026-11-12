# Security and data handling

This local SYNTHETIC-only demonstration contains no real protected health information
(PHI). Never submit real patient data, credentials, internal system IDs or record exports.
The API accepts bundled fixture IDs, not patient-record uploads. Free-text reasons and
actor labels must also be fictional. Demo roles are unauthenticated; they are workflow
labels, not access control for a real deployment. Bind only to 127.0.0.1.

Report a vulnerability privately to wpkreg@gmail.com, with a minimal synthetic reproducer,
affected version and expected/actual behavior. Do not include real data or secrets in an
issue, email, screenshot, log or attachment. There is no promised response SLA.

If someone accidentally submits real data: stop processing it; do not quote, download,
repost, or add it to tests. Ask the maintainer privately to remove the content and any
attachments. Restrict access while removal is arranged. For local runs, stop the service
and remove affected SQLite files, journal files and captured logs/backups. If committed,
coordinate removal from history and copies; deleting only the latest file is insufficient.
Rotate any exposed credentials with their owner. Retain only a data-free incident note.

There is no encryption-at-rest, authentication, clinical audit compliance, background
expiry worker or production hardening. Persisted local files are the operator's responsibility.
Confirmed cases still contain draft proposals; no order-execution integration exists.
