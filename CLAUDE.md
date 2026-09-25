# STIR — persistent agent context

Read this before touching any STIR repo. It exists so a fresh session does not
re-derive the architecture from scratch. It references documentation; it does
not duplicate it. If code and docs disagree, report the conflict — do not
silently pick one.

## Repositories

Five independent Git repos, siblings under `stir/` (itself `stir-workspace`,
public, coordination-only — README, this file, `.code-workspace`):

- `stir-backend` (Java/Spring Boot/Flyway/PostgreSQL/RLS)
- `stir-frontend` (React, JavaScript not TypeScript)
- `stir-main` (deploy: Docker Compose, vendor pinning, E2E/smoke scripts, `update.py`)
- `stir-doc` (architecture + validation record — read before touching a domain
  below; code and tests still win over stale docs)

STIR depends on IDAX Core (`idax-shell`, `ostris`, `idax-ledger`, all at
`github-public/`) as pinned public vendor sources (`upstream.lock.json` in
`stir-main`). Never hand-edit vendor code inside `stir-main/vendor/` — fix it
at the source repo, bump the pin, `python scripts/initialize.py`.

## Git workflow

One branch per capability: `claude/<capability>-mvp` (good:
`claude/dispute-resolution-mvp`; bad: `claude/add-button`). Branch immediately
after baseline verification, before any edit — never edit on `main` directly.
Commits: coherent per concern (`backend/domain`, `frontend/ux`, `e2e/docs`),
not one giant commit, not fifty microscopic ones. Merge to `main`,
fast-forward when possible, push. No force-push, no destructive rebase of
shared branches, no squash that erases the increment's internal structure.

Local checkouts are **shared with Codex**, working in parallel on the same
machine. `git checkout` in one session silently redirects the other's next
commands. Always check `git branch --show-current` before assuming state.

## MVP philosophy (non-negotiable pace)

The unit of delivery is a **complete functional capability**, not a table, a
class, an endpoint or a test. Group domain + DB + Flyway + RLS + permissions +
backend + API + frontend + i18n + tests + E2E + docs into one increment.
Prefer 3 large phases over 30 microfeatures. Done means "STIR can now do X
end-to-end", demoable in a browser or a real E2E script — not "X is prepared
for Y later." No new abstraction, framework, DSL or service ahead of a real
need.

## Tenant / workspace model

A superuser can create an isolated workspace (tenant) from the idax-shell
admin UI (`TenantAdminController` in `idax-shell`). Each workspace gets its
own tenant, STIR marketplace, osTRIS economic community, and RLS-enforced
isolation. `TenantOnboardingService` (idax-core) is unused for this — it
forces a nonexistent AX4 legacy `idax.dataarea` table STIR never provisions.
Creation instead composes `TenantCreateRepository` + `TenantUserService` with
explicit `SET LOCAL ROLE idax_admin` + `idax_core.set_tenant(...)` +
`TenantContext` elevation. Do not reintroduce the DataArea dependency.

Test tenant: **`stir-pruebas`** (slug `stir-pruebas`). Prefer it for anything
destructive, adversarial, or synthetic (manipulation drills, governance
recovery, fake evidence). Do not contaminate the real `STIR` tenant's market
evidence with test data unless there is no alternative — and say so if you do.

**Platform administration is not community governance.** A superuser can
create/enable/disable/rename a tenant. That grants nothing over Seven Keys,
Guardian, references, or RLS-protected data. Verified: Seven Keys endpoints
check `TenantContext`-scoped `stir.references.*` permissions, never the
superuser principal flag; the DB role platform actions run under
(`idax_admin`) has its constitutional-mutation columns explicitly revoked
(`V9__restrict_constitutional_mutation_role.sql`); a real Testcontainers test
(`SevenKeysPostgresTest.adminDatabaseRoleCannotRotateOrUnsuspendConstitutionalSeat`)
proves it. Creating a tenant never bootstraps Seven Keys — bootstrap is a
separate, explicitly permissioned, real-Ed25519-signed HTTP call
(`stir.references.publish`). No server-side secret-key generation exists or
should be added.

## Economic exchange boundary (STIR ↔ osTRIS)

`Agreement` (STIR) → `AgreementSnapshot` → osTRIS `EXCHANGE` (committed
ledger). osTRIS never interprets goods, services, price, or "fair value" —
that stays STIR's responsibility. A real signed transaction requires the
participant's own signature; never simulate or bypass it.

## Community Value References, Market Integrity, Seven Keys

Full design: `stir-doc/COMMUNITY_VALUE_REFERENCES.md`,
`MARKET_INTEGRITY.md`, `SEVEN_KEYS_GOVERNANCE.md`,
`GOVERNANCE_CAPTURE_THREAT_MODEL.md`, `CREDENTIAL_RECOVERY.md`. Validation
record: `VALIDATION_COMMUNITY_VALUE_REFERENCES.md`,
`VALIDATION_MARKET_INTEGRITY.md`.

Five distinct concepts, never collapse them: unit of account → observation →
community value reference → agreed value → committed ledger entry. An
observation does not auto-publish a reference; a reference does not bind
either party; the Agreement keeps the value actually agreed.

Seven Keys: exactly 7 constitutional seats per tenant+community authority
(`stir.constitutional_authority`, unique on `(tenant_id, community_id)`), plus
one separate non-voting Guardian per authority. `AMEND_CONSTITUTION`,
`REMOVE_GUARDIAN`, `APPOINT_GUARDIAN`, `ROTATE_CREDENTIAL` need 7-of-7 (no
6-of-7 fallback — ever). Guardian can `EMERGENCY_SUSPEND_CREDENTIAL` (one at a
time) and be removed 5-of-7 without its own signature. The Guardian governs
nothing. Domain-separated Ed25519 signing bytes prevent replay across
action/proposal/community/tenant.

**`REPLACE_CONTROLLER` is deliberately fail-closed** —
`FINAL_RESOLUTION_VERIFICATION_UNAVAILABLE` regardless of signatures, because
osTRIS has no generic, tenant-scoped, verifiable finality contract. Do not
implement a client-supplied `finalResolutionId` shortcut; that would make
recovery a superkey. This is a standing SPEC GAP (see below), not a bug.

Never introduce `superAdmin`/`masterKey`/`rootOverride`/`forceReference`/
`forcePrice`/`forceTransaction`/`ignoreConstitution`/
`lowerThresholdForEmergency` or any semantic equivalent (e.g. a threshold
field quietly settable to 0 through an ordinary policy API).

## Standing SPEC GAPs (do not improvise past these)

1. **Final-resolution verification contract** — a generic, privacy-preserving
   osTRIS contract proving community/subject/scope/authority/finality/appeal
   state/digest, usable by `REPLACE_CONTROLLER` without STIR-specific
   semantics leaking into osTRIS. Until it exists, controller replacement
   stays blocked.
2. **Identity continuity / related-account clustering** — STIR sees accounts
   and relationships between accounts, not independent people
   (`ACCOUNTS_ONLY_RELATED_ACCOUNTS_UNKNOWN`). A lawful, privacy-preserving
   adapter is needed before automated identity-cluster claims are anything
   more than an unverified signal.
3. **Catastrophic multi-key recovery** — losing two-plus seat credentials at
   once (or a seat plus the Guardian) has no recovery path: same-controller
   rotation needs the Guardian + the other 6-of-6 active seats, and there is
   deliberately no fallback threshold, master key, or SuperAdmin path around
   that. Fail-closed by design (`GOVERNANCE_CAPTURE_THREAT_MODEL.md`); a real
   design almost certainly needs out-of-band, real-world re-attestation of
   seat-holder identity before reinstating a credential.

If a task needs any of these, stop and present alternatives — do not design a
private workaround.

## Seven Keys custody — what the guarantees actually are

Non-extractable WebCrypto (`governance-signer.js`, `signer.js`) means the raw
key bytes cannot be exported off the device holding them — real, but it does
not mean the key can't be misused *in place* by a compromised client (a
malicious extension, a compromised dependency/OS could still ask the
`CryptoKey` to sign an attacker-chosen message). Never phrase this guarantee
as "cannot be used by an attacker." Same-device bootstrap (all 7 seats + the
Guardian generated/signed in one browser) is a dev/E2E/demo/`stir-pruebas`
fixture, not a real ceremony — one device holding many credentials is not
seven independent custodians. The bootstrap UI says so; keep it saying so,
and never let UI copy imply an independence guarantee that a same-device flow
does not provide.

## Gates before declaring a domain increment done

Backend: `mvn verify` with real PostgreSQL/Testcontainers (never skip the
Docker-dependent classes and call it done), Flyway from empty, RLS/tenant
isolation. Frontend: `npm test`, `npm run build`, `npm run i18n:validate` (12
locales, keep key sets identical — see root `AGENTS.md` i18n rules, same
discipline applies here even though this is not the IDAX Core repo).
E2E: real HTTP + real browser scripts in `stir-main/scripts/`, not mocks,
against the local dev stack (`docker compose -p stir-dev`, see
`stir-main/compose.yml`; `python scripts/update.py` pins vendor + rebuilds +
health-checks + smoke-checks in one step). Stop any container you started for
verification when done; leave what was already running alone.

## What Claude decides alone vs. escalates

Decide and continue: internal structure, classes, components, UX, non-
normative APIs, queries/indexes, local refactors, test structure, i18n,
technical docs, dedup, which of several reasonable implementations to pick.

Stop and ask: an irreversible action, a normative SPEC GAP, a protocol
change, a change to a fundamental invariant (the two SPEC GAPs above, the
7-of-7 threshold, Guardian non-governance, append-only market/reference
history, RLS as the last boundary), a critical security issue, or an
architectural decision that would move an existing boundary (STIR/osTRIS,
platform-admin/community-governance, generated/custom).
