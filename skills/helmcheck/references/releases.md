# Releases

## Component updates

- Example environment files: `qa-values.yaml`, `beta-values.yaml`, `prod-values.yaml` and `preview-values.yaml`.
- Example update flow:

| Event | Chart source | Values changed | Review target |
| --- | --- | --- | --- |
| QA component build | Current development chart | QA | QA update PR |
| Release component build | Chart prepared for beta | Beta | Beta release PR |
| Beta promotion | Tested beta chart | Prod image versions | Prod promotion PR |
| Urgent prod fix | Current prod chart | Affected prod component | Separate hotfix PR |

- Collect component updates in one open PR per target environment. Preserve earlier updates when another component arrives.
- Accept only known component names. Resolve the digest for the reported tag before changing its image value.
- Example digest lookup, with `image` set to the component's repository and release tag:

```bash
docker buildx imagetools inspect "$image" --format '{{.Manifest.Digest}}'
```

- Use the returned digest in the image reference. Do not resolve the tag again during beta-to-prod promotion.
- Show each component's old and new version in the PR. Mark downgrades for review.
- Take prod configuration from prod values while taking chart code and image versions from beta. Do not copy beta hosts, credentials or replica settings over prod.

## Preview lifecycle

- Give each source change a stable preview ID and a dedicated chart branch and PR.
- Reuse an open preview PR. Reopen a closed, unmerged one when the preview is requested again.
- Refresh active previews after changes to the base chart. Report merge conflicts.
- Tie preview resources to that ID, including namespace, host, config references and any dedicated data services.
- Closing the preview PR must reach the controller that removes its resources. Deleting a Git branch alone does not prove cleanup.
- Keep preview settings in their own values layer so a component version update does not replace them.

## CI integration

- Call the same chart validation workflow from normal PRs, component update PRs and promotion PRs. Its path and name belong to the chart repository.
- Include beta in the environment matrix. For previews, provide explicit test inputs for values normally supplied by the preview controller.
- Treat changes to values, helpers, dependencies and policies as reasons to revalidate their consumers.
- Use [validation commands and policy examples](validation.md) for the shared check.
- Keep chart checks as required PR checks before promotion.
