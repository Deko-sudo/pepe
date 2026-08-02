# W6 CI main-push security gates

> Status: W1, W2, W3, W4, and W5 are merged. W6 is delivered by the current pull request, but awaits exact-head contract and Docker CI evidence followed by owner merge approval. W7 is not started. Production activation, provider activation, hosting, DNS, TLS, Telegram device validation, and Stage 9 are out of scope.

## Scope

The `CI` workflow runs on pull requests targeting `main` and on pushes to `main` (as well as the repository's existing `develop` push coverage). The repository commit is the only input in both contexts; the workflow neither uses pull-request-only metadata nor deploys or publishes anything.

`Wrapper CI security contract` is the W6 gate. It runs `scripts/verify_wrapper_ci_contract.py`, a standard-library structural verifier that rejects drift from the required PR/main triggers, least-privilege permissions, wrapper browser suite, Docker smoke dependency graph, and local-only provider boundary. The verifier makes no network request.

The existing required jobs remain part of the same workflow: Frontend, API, Quote Core, Migration, Bot, Worker, Worker integration, Stage 7 worker integration, TradingView wrapper, and Docker. The wrapper suite uses deterministic loopback synthetic fixtures; Docker smoke requests only local Mini App, API, and wrapper routes. Mutable-script and subresource verification commands remain manual-only because they can contact provider endpoints and must not run in CI.

## Security model

Workflow-level permissions are explicitly `contents: read`; the W6 job also declares the same permission and checks out with `persist-credentials: false`. The workflow has no `pull_request_target`, write permission, deployment, artifact publication, production secret, public provider request, or Telegram production credential path.

Failures are visible as required CI failures. Remediation is to correct the repository-controlled workflow, verifier, or affected deterministic suite, then obtain a successful CI run for the new exact commit SHA. Do not bypass required checks or use auto-merge.

## Local reproduction

```text
python scripts/verify_wrapper_ci_contract.py
make lint
make typecheck
make test
make build
```

GitHub event dispatch itself is not reproducible locally. The verifier structurally proves both `pull_request` targeting `main` and `push` to `main` use the repository commit and invoke the mandatory W6 contract gate. Exact-head PR CI, including the contract and Docker jobs, is required before W6 readiness. No direct push to `main` is used for pre-merge testing.

W7 remains responsible for Telegram device validation, infrastructure, and any production activation. Written TradingView confirmation remains mandatory before production activation.
