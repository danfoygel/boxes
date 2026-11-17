# Agent instructions

## Never open pull requests upstream

This repository is a personal fork: `danfoygel/boxes` (remote `origin`).
It was forked from `florianfesti/boxes` (remote `upstream`).

- **Never open, push to, comment on, or otherwise touch pull requests or
  issues on `florianfesti/boxes`.** This applies even when the change
  looks like a good upstream contribution.
- All pull requests target `danfoygel/boxes`, base branch `master`.
- Push branches only to `origin`. Never push to `upstream`.
- `gh` picks the `upstream` remote by default when it exists, so always
  pass the repository explicitly:

  ```bash
  gh pr create --repo danfoygel/boxes --base master ...
  ```

  Do the same (`--repo danfoygel/boxes` or `-R danfoygel/boxes`) for
  every `gh pr`, `gh issue`, and `gh api` call.
- If you're about to make a `gh` call and aren't sure which repository it
  will hit, run `gh repo set-default --view` first. It must print
  `danfoygel/boxes`.
