# Changelog

## 0.5.0-rc1

STIR 0.5 Public Beta hardening: coordinates the same increment across stir-doc, stir-backend,
stir-frontend and stir-main - no new product functionality, the 0.4 software made
production-deployable (clean-build gate, production Compose topology with real TLS, a security
gate that found and fixed public Swagger exposure on every Spring service, automated backup
retention, deploy/status/rollback operations, and a genuine IDAX Shell permission-visibility fix
upstreamed as a public Shell patch instead of a second STIR-side workaround). See each
repository's own CHANGELOG for detail, and stir-doc/VALIDATION.md's 0.5 section for the full
evidence and the exact external-infrastructure gaps still blocking a real stir.es deployment.

## 0.2.0-SNAPSHOT

STIR 0.2 Marketplace MVP: coordinates the same increment across stir-doc, stir-backend, stir-frontend and stir-main. See each repository's own CHANGELOG for detail.

## 0.1.0-SNAPSHOT

Independent workspace coordination for the four STIR product repositories.
