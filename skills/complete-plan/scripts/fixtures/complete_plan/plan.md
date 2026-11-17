# Retry the sync

**Goal:** Retry a failed sync one time.

**Kind of change:** feature

## Intent

The sync fails on a short network error.

## Decisions

- **Retry one time** — two passes are enough.
- **No backoff state** — the user rejected a status field.

## Traps

- `sync.go` wraps the error two times.

## Definition of Done

- [x] A failed sync runs again — proof: a test.

## Wrap-up

- [x] all tests pass: `go test ./...`
- After all boxes: run `/amoniac:complete-plan`. The user deletes the plan with `! rm`.
