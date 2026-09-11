# STIR workspace — 0.2.0-SNAPSHOT

Development coordination for Sistema Transparente de Intercambio de Recursos.
This directory is the independent **stir-workspace** repository, locally named **stir**.

Open `stir.code-workspace`. Four sibling repositories inside this folder remain independent Git histories: stir-doc, stir-backend, stir-frontend and stir-main. They are deliberately ignored here, not submodules or gitlinks. Deployment, Docker Compose and public upstream initialization belong to stir-main. No remote URLs have been assigned to STIR.

Run the STIR: initialize, validate, start, status, smoke and stop tasks. Requirements and local credentials instructions are in stir-main/README.md; architecture and evidence are in stir-doc.

Source releases must come from each repository's tracked content with `git archive` or the hosting provider's source archive. Never ZIP the physical workspace: ignored secrets, vendor clones, caches, compiled artifacts and logs are not release inputs. Public upstreams are obtained through stir-main's pinned initializer.

STIR source is Apache-2.0. IDAX Core's public binary remains separately licensed. No economic operations or production deployment are included.
