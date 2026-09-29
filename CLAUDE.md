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

**Platform capability grants must never be interpreted as community
governance authority.** idax-core's `PermissionService.hasPermission(user,
permission)` unconditionally returns `true` for `user.isSuperuser()`, for
every permission string, confirmed by decompiling the vendored jar and
empirically (see `GOVERNANCE_CAPTURE_THREAT_MODEL.md`). `@PreAuthorize`
alone therefore cannot be the boundary for a community-governed mutation.
The fix is `ReferenceService.requireCommunityAuthority(CurrentUser user)` — a
single, reusable, package-private static check called as the *first
statement* inside every sensitive mutation
(`ReferenceService.create/policy/propose/publish`,
`MarketIntegrityService.signal/decide`), so the rejection holds at the
service layer regardless of which controller — or any future non-HTTP
caller — reaches it. `ReferenceController`/`MarketIntegrityController` call
the same method again at the top of their handlers as defense-in-depth, not
a duplicated implementation. Ordinary reads on both controllers are
deliberately left permission-gated only — this check protects mutation
authority, not all of STIR. `SevenKeysController` has no such guard and does
not need one: its real protection is the Ed25519 signature requirement,
independent of the HTTP permission layer, so a superuser token still cannot
forge a seat's vote or Guardian action — a real Testcontainers test
(`SevenKeysPostgresTest.adminDatabaseRoleCannotRotateOrUnsuspendConstitutionalSeat`)
proves the DB-role side of that (the constitutional-mutation columns are
revoked from `idax_admin`, `V9__restrict_constitutional_mutation_role.sql`).
Any other `stir.*`-gated controller/service added later inherits the
superuser bypass until it adds the same explicit `requireCommunityAuthority`-
style check at its own service layer — check for it, don't assume
`@PreAuthorize` alone is sufficient. `ReferencePostgresTest` proves the
service-layer rejection directly (no controller in the path), a
community-authorized actor succeeding at the same operation, and that
switching tenant context grants no cross-tenant authority; the HTTP E2E
(`community_value_governance_e2e.py`) proves the same six mutations reject a
real superuser session while that session's legitimate platform actions
(role creation, user provisioning) still succeed. Creating a tenant never
bootstraps Seven Keys — bootstrap is a separate, explicitly permissioned,
real-Ed25519-signed HTTP call (`stir.references.publish`). No server-side
secret-key generation exists or should be added.

## Economic exchange boundary (STIR ↔ osTRIS)

`Agreement` (STIR) → `AgreementSnapshot` → osTRIS `EXCHANGE` (committed
ledger). osTRIS never interprets goods, services, price, or "fair value" —
that stays STIR's responsibility. A real signed transaction requires the
participant's own signature; never simulate or bypass it.

## Community Value References, Market Integrity, Seven Keys

Full design: `stir-doc/COMMUNITY_VALUE_REFERENCES.md`,
`MARKET_INTEGRITY.md`, `SEVEN_KEYS_GOVERNANCE.md`,
`GOVERNANCE_CAPTURE_THREAT_MODEL.md`, `CREDENTIAL_RECOVERY.md`,
`PARTICIPANT_INDEPENDENCE.md`, `ORDINARY_GOVERNANCE.md`. Validation
record: `VALIDATION_COMMUNITY_VALUE_REFERENCES.md`,
`VALIDATION_MARKET_INTEGRITY.md`, `VALIDATION_SEVEN_KEYS_UI.md`,
`VALIDATION_COMMUNITY_VALUE_GOVERNANCE.md`,
`VALIDATION_ORDINARY_GOVERNANCE.md`.

**Ordinary community governance** (`ORDINARY_GOVERNANCE.md`) is a real,
quorum-based, non-constitutional decision process, opt-in per community
(`stir.community_governance_settings`, default off - every delegated-
publisher flow stays unchanged until a community turns it on). Its
electorate (`stir.community_governance_member`) is a wholly STIR-owned
roster, never derived from IDAX Core/Shell roles or permissions (no such
"everyone holding permission P" query exists safely without a new
cross-service credential) - so platform SuperAdmin, the Guardian, and a
Seven Keys constitutional seat all grant no vote here by themselves; only
explicit membership does. Execution reuses the exact same
`ReferenceService.publishDirect()`/`policyDirect()` methods the delegated-
publisher path already validates - a constitutional-floor-crossing proposal
is refused even after unanimous approval, by construction. There is no
`approveProposal(id)` anywhere in this codebase.

Five distinct concepts, never collapse them: unit of account → observation →
community value reference → agreed value → committed ledger entry. An
observation does not auto-publish a reference; a reference does not bind
either party; the Agreement keeps the value actually agreed.

The full publisher toolkit has a UI now (`stir-frontend/src/references.jsx`):
propose/publish (pre-existing), plus raw/eligible/excluded evidence breakdown
with reason codes (`EvidenceBreakdown`, reading the private
`observations()`/`evidenceManifest()` endpoints — full participant/amount
detail, gated on `stir.references.publish`, never on read), reference policy
configuration inside constitutional floors (`PolicyForm`), and the market
integrity SIGNAL→UNDER_REVIEW→FINAL/DISMISSED review workflow
(`IntegrityPanel`). A same-day observation is structurally invisible to
`evidence-manifest` (`snapshot()`'s SQL filters `observed_at < cutoff`) —
don't design a test or a UI affordance that expects same-day eligibility to
change live; `VALIDATION_COMMUNITY_VALUE_GOVERNANCE.md` explains why and what
that means for testing.

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

## Consent and retention for reference evidence

Full design: `stir-doc/CONSENT_RETENTION.md`. Validation:
`VALIDATION_CONSENT_RETENTION.md`.

Four questions, never collapsed into one: having a datum
(`reference_observation`, always recorded regardless of consent) → having
permission to use it (`reference_consent`/`reference_consent_event`,
purpose-specific, captured automatically at Agreement acceptance from the
existing bilateral `shareReferenceObservation` flow, withdrawable later by
either party as a personal, self-service right) → still being allowed to
retain it (`retention_policy`, versioned, community-scoped, floor
`RetentionService.MINIMUM_RETENTION_PERIOD_DAYS = 90` as a **code constant**,
deliberately not a Seven Keys constitutional field) → still eligible as
current evidence (`EvidenceAnalysis`'s existing live exclusion set, now also
`CONSENT_WITHDRAWN`, never rewriting a cached `reference_snapshot`).

**Consent withdrawal never rewrites history.** `aggregate_consent` frozen on
an observation at acceptance time is never mutated; withdrawal only ever
changes eligibility for a future, not-yet-cached daily cutoff via a
separate, live-queried exclusion set threaded into the same
`finalExclusions` map Market Integrity already used - `FINAL_INTEGRITY_FINDING`
always outranks `CONSENT_WITHDRAWN` in the reason shown, so withdrawing
consent can never look like erasing evidence of manipulation.

**Retention's one real action, anonymization, has a dedicated narrow
trigger.** `reference_observation` was fully append-only (V5); rather than
weaken that, it now has its own `reject_reference_observation_mutation()`
trigger permitting *exactly one* transition
(`participant_a`/`participant_b` → `NULL`, `anonymized_at`/`anonymized_by`
set, nothing else ever changes, no `DELETE` ever allowed) - not even a real
Postgres superuser can bypass it without `SET session_replication_role =
'replica'`, a bar this codebase's own SQL fixtures now have to clear
deliberately for backdating (there is no HTTP path to backdate
`observed_at`, and there should never be one). A market-integrity case in
any status unconditionally blocks anonymization, regardless of retention
age - retention never overrides an open investigation, and consent
withdrawal never deletes anything by itself.

**Ordinary Governance gained a community-scoped proposal type**
(`RETENTION_POLICY_CHANGE`, `ordinary_proposal.definition_id` widened to
nullable) specifically so enabling governance never silently freezes
retention-policy changes with no proposal path to replace them - the same
"don't half-wire a gate" discipline as everything else in this bounded
context.

## Multi-source value evidence: LISTING, WANTED, COMMUNITY_SEED

Full design: `stir-doc/MULTI_SOURCE_VALUE_EVIDENCE.md`. Validation:
`VALIDATION_MULTI_SOURCE_VALUE_EVIDENCE.md`.

LISTING/WANTED reuse the existing `Listing` entity (`direction`), gaining an
opt-in, owner's-own indicative price and a purpose-specific unilateral
consent (`ConsentService.LISTING_PURPOSE`, never the bilateral
`AGREEMENT_PURPOSE`). **A later edit never rewrites an earlier
observation** - `ListingRevision` (immutable, mirrors `AgreementSnapshot`)
freezes every create/update, and a `reference_observation`'s `source_id`
points at the revision, never the mutable `Listing.id`. `ListingEvidenceAdapter`
is the *only* crossing point from listing into the reference bounded
context, same role `ReferenceAcceptanceAdapter` already had for Agreements.

**Economic lineage prevents one process from becoming several independent
voices.** `reference_observation.economic_lineage_id` threads the
originating `Listing.id` through LISTING/WANTED and any PROPOSAL/AGREEMENT
descending from it (via `negotiation.listingId`) - no new UUID, the listing's
own id is the correlation key. `EvidenceAnalysis` groups included
observations by this key and reports `economicLineageCount`/
`maximumLineageShare`, with a new `LINEAGE_CONCENTRATED` signal reusing the
existing participant-share threshold rather than a second, invented number.

**Each source stays its own bucket, never one blended weighting.**
`reference_policy.listing_source_enabled`/`wanted_source_enabled` (both
false by default) gate a *separate* `EvidenceAnalysis.analyze()` call per
source (`Policy.forSource(...)`), folded into `snapshot()` as
`listingEvidence`/`wantedEvidence` sub-objects - never merged into the
AGREEMENT median/IQR. `sourceBreakdown` (raw per-source counts) is always
computed, unconditionally, so a publisher can see "AGREEMENT: 18, LISTING:
11, ..." without that ever being presented as 18+11 equally-weighted votes.
A unilateral bucket (`requiresCounterparty=false`) skips relationship/pair-
based independence checks (meaningless with one party) but is held to the
exact same constitutional `minimumParticipantFloor`/`minimumObservationFloor`
as AGREEMENT - widening the input surface never relaxes that floor.

**Community Seed has no delegated-publisher path at all** - unlike every
other publish/policy mutation in this codebase, `stir.community_seed` has
exactly one writer, `ReferenceService.insertSeedDirect()`, callable only from
`OrdinaryGovernanceService.execute()`'s approved-proposal dispatch. Platform
SuperAdmin cannot propose, vote on, or execute a seed by virtue of being
SuperAdmin, same `requireCommunityAuthority()` gate as everything else
governance-related. A seed is never a market observation (no
`reference_observation` row, no `economic_lineage_id`), and a later seed is
always a new version - the previous one is never rewritten. Whether/how a
superseded seed (`supersededByRealEvidence` fires once the AGREEMENT bucket
itself reaches `SUFFICIENT_DATA`) should eventually stop being shown is an
explicit, open **SPEC GAP** - not an automatic invalidation formula, and not
something to improvise past.

LISTING/WANTED are cheaper to fabricate than AGREEMENT - `MarketIntegrityService`
gained seven new, still human-raised-only signal codes for that surface
(listing spam, coordinated postings, temporal bursts, lineage manipulation,
selective consent patterns, artificial seed orientation), same `SIGNAL ≠
FINDING` discipline as `MARKET_INTEGRITY.md`.

## Community extension boundary (FreeFolk Market and other distributions)

Full design: `stir-doc/COMMUNITY_EXTENSION_GUIDE.md`,
`FREEFOLK_MARKET_PREPARATION.md`, `MIXED_CONSIDERATION_EXTENSION.md`.
Validation: `VALIDATION_COMMUNITY_EXTENSION.md`.

STIR is upstream; FreeFolk Market (or any other distribution) is never a
fork. The dependency is always `distribution → STIR`, never the reverse —
no distribution-specific code, table, or import belongs in STIR or osTRIS.
What's actually upstream today, all additive and backward-compatible:

- `stir-frontend/src/catalog-client.js` — a dependency-free ESM catalog/
  offer contract (`CATALOG_CONTRACT_VERSION`). STIR's own UI
  (`listing.jsx`/`extension.jsx`) is its first consumer, not a parallel
  copy; a second presentation (`examples/community-catalog/`) proves reuse
  without copying internal sources.
- An opaque external-contract commitment on `Offer`/`Agreement`
  (`externalContractNamespace`+`externalContractDigest`, both-or-neither,
  frozen into the snapshot at `schemaVersion=3`). STIR never interprets
  it — no FIAT, fee, or fiscal semantics anywhere in STIR/osTRIS.
- A minimal, honest version-compatibility surface on the public
  `GET /api/stir/instance`: `stirVersion`, `catalogContractVersion`,
  `externalContractSchemaVersion` — the only versions STIR actually
  enforces, not a capability-registry framework. A distribution's own
  lock/compatibility record decides what it requires; STIR only declares
  what's deployed right now.

Explicitly not built, and not to be built speculatively: a generic plugin
framework, a capabilities-discovery endpoint beyond the three version
fields above, any FIAT/PSP/fee/fiscal-valuation code in STIR core or
osTRIS, or SQL/privileged-service credentials granted to an extension. An
extension can add capabilities; it can never bypass RLS, tenant isolation,
Community Authority, Ordinary Governance, Participant Independence, Market
Integrity, Seven Keys, constitutional bounds, or osTRIS's own
authorization/invariants — platform SuperAdmin is not Community Governance
Authority for an extension any more than it is for STIR itself. The osTRIS
`purpose=SETTLEMENT` value used by an external marketplace-fee experiment
is an open SPEC GAP — `OSTRIS_INTEGRATION.md` gives it no support beyond
STIR's own `purpose=EXCHANGE`; do not invent or ship code that sends it.

## Standing SPEC GAPs (do not improvise past these)

1. **Final-resolution verification contract** — a generic, privacy-preserving
   osTRIS contract proving community/subject/scope/authority/finality/appeal
   state/digest, usable by `REPLACE_CONTROLLER` without STIR-specific
   semantics leaking into osTRIS. Until it exists, controller replacement
   stays blocked.
2. **Identity continuity / related-account clustering — partially closed.**
   `PARTICIPANT_INDEPENDENCE.md`: STIR now consumes osTRIS's own real,
   already-shipped private continuity decisions (`ostris.risk_subject`/
   `IdentityContinuityDecision`) through a minimal, publisher-triggered,
   non-live-reused projection (`stir.participant_independence_projection`),
   correcting diversity/concentration down when osTRIS has confirmed two
   accounts related. What remains open: osTRIS never affirmatively
   certifies independence (only ever confirms/contests/rejects one
   relatedness claim), so accounts with no data stay honestly
   `INDEPENDENCE_UNKNOWN`, never assumed independent; a fully automatic
   (non-publisher-triggered) refresh would need a new STIR→osTRIS service
   credential, deliberately not built. Relationship-diversity counting is
   now cluster-aware for the hub-sharing-a-cluster pattern
   (`clusterAdjustedRelationships`/`assuredIndependentRelationships`/
   `unknownRelationships`, reported separately, never conflated) and
   refresh-coverage integrity has its own reproducible reason
   (`INSUFFICIENT_INDEPENDENCE_COVERAGE`) rather than an estimate — see
   that doc's "Hardening" sections for what's covered and what remains
   open (cluster identity shared across different account pairs with no
   common hub).
3. **Catastrophic multi-key recovery** — losing two-plus seat credentials at
   once (or a seat plus the Guardian) has no recovery path: same-controller
   rotation needs the Guardian + the other 6-of-6 active seats, and there is
   deliberately no fallback threshold, master key, or SuperAdmin path around
   that. Fail-closed by design (`GOVERNANCE_CAPTURE_THREAT_MODEL.md`); a real
   design almost certainly needs out-of-band, real-world re-attestation of
   seat-holder identity before reinstating a credential.
4. **Community Seed supersession rule** — a Community Seed's
   `supersededByRealEvidence` flag (`MULTI_SOURCE_VALUE_EVIDENCE.md`) is a
   live, honest signal that real AGREEMENT evidence now exists, deliberately
   not an automatic invalidation formula. Whether/how a superseded seed
   should eventually stop being shown, versus staying as historical context
   forever, versus requiring a fresh governance vote to retire it, is open.

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

A seat/Guardian may instead be backed by a real WebAuthn/hardware
credential (`WEBAUTHN_HARDWARE_CUSTODY.md`) — `WebAuthnCrypto.java`
verifies ES256/RS256/EdDSA assertions, attestation format `"none"` only (no
trust chain, no metadata service), with the WebAuthn challenge bound to
`base64url(SHA-256(domain-separated JCS payload))` so a captured assertion
can't be replayed for a different proposal/community/tenant/seat, plus the
authenticator's own `sign_count` for native clone/replay detection —
stronger than governance-signer.js's non-extractable WebCrypto (the key
material never touches this origin's JavaScript at all), still not an
absolute guarantee for the same reason above. `CredentialEnvelope`
generalizes both credential types through the same verification path;
every new field is additive, so the Ed25519 path is unchanged for every
existing call site. Known gap, not yet fixed: `CredentialRegistrar`
(`governance.jsx`) has no raw "paste a public key obtained on another
device" input, so `ROTATE_CREDENTIAL`/`REPLACE_CONTROLLER`'s incoming
WebAuthn credential currently must be generated/registered on the same
device driving that proposal's UI — bootstrap's own cross-device
invitation/contribution paste flow is unaffected.

## `idax_app` can write governed state directly (`AUD-012`, HIGH, open)

`idax_app` (and `idax_backend`, which inherits it) keeps ordinary `INSERT` on 45/48 STIR tables
even after V17 revoked all `idax_admin` DML — V17 closed the platform-admin vector
(`AUD-004`/`AUD-006`), not the runtime-credential one. Anyone with SQL access under that
credential can insert an unsigned `market_constitution` row or a bare `FINAL`
`market_integrity_case_event` with no prior `SIGNAL`/`UNDER_REVIEW` — no RLS policy or business
check runs on `INSERT`, only on `UPDATE`/`DELETE`. `stir-doc/FULL_SYSTEM_AUDIT.md`'s `AUD-012`.

A Phase 1 tamper-evident audit MVP (`stir-doc/VALIDATION_GOVERNED_STATE_AUDIT_MVP.md`,
implemented in an isolated worktree, never merged) adds a `SECURITY DEFINER` trigger on 40/47 real
`stir.*` tables, owned by a new `stir_audit_owner` role `idax_app`/`idax_admin` can never touch,
writing an append-only, hash-chained `stir_audit.mutation_event` a separate `stir_auditor`
credential (its own secret, read-only on `stir.*`) verifies. This **detects** both `AUD-012`
attacks reproducibly - it does not prevent them, does not close `AUD-012`, and its
`VerificationVerdict` enum has no `PASS_AUTHORIZED` value: a self-consistent SQL-fabricated
governance history classifies at most `PASS_STRUCTURE_ONLY`, on purpose. `PASS_CRYPTO` was never
implemented in Phase 1 (would require independently reimplementing Ed25519/WebAuthn + RFC 8785 JCS
verification without depending on `SevenKeysCrypto`/`WebAuthnCrypto`, which would make the backend
implicitly authoritative over the verifier's own results) - see the validation doc's SPEC GAP list
before assuming any domain's classification means more than structural consistency.

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
