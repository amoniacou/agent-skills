---
name: helmcheck
description: Use before writing, changing or reviewing Helm charts, values, shared helpers, migration hooks or chart validation.
when_to_use: Before editing Chart.yaml, values*.yaml, environment values, chart templates, library helpers, skaffold.yaml, kind scripts or chart CI. When reviewing rendered manifests, changing workload settings or debugging a failed release. Also on "helm", "chart review", "helm template", "migration hook".
---

# Helm Charts

## References

- Read [deployments](references/deployments.md) when creating or reviewing a Deployment and its Service.
- Read [shared containers](references/shared-containers.md) when several services repeat the same runtime setup.
- Read [migrations and hooks](references/migrations-and-hooks.md) when changing release tasks or startup order.
- Read [availability](references/availability.md) when changing PDB, worker HPA, PriorityClass or maintenance routing.
- Read [releases](references/releases.md) when changing version promotion, previews or release CI.
- Read [validation](references/validation.md) when checking a chart or changing its CI and Rego policies.

## Templates and values

- Make the application meet the chart's requirements. Do not weaken runtime rules for developer convenience.
- Group manifests by service. Keep resource structure visible in templates.
- Use application charts for deployable resources and library charts for reusable named templates.
- Reuse existing library helpers for names, labels, secret references and dependency checks.
- Extract a container helper when many apps share the same runtime setup, as with Rails Puma, Sidekiq and migrations. Keep the common setup and runtime rules in that helper.
- Do not copy the Kubernetes API into helper parameters. Merge native container YAML over the shared setup so each app can tune it. Validate the merged result against the runtime rules below.
- Put deployment differences in values and fixed rules in templates. Use `required`, not `default`, for app-specific helper inputs and values without a safe default. Name the missing key in the error.
- Keep shared defaults separate from environment overrides. Use camelCase keys and quote strings.
- Use standard labels on resources and pod templates. Use stable name, release and component labels in selectors. With the common library, use `common.labels.standard` and `common.labels.matchLabels` plus `tier`.
- Apply each optional component's gate to all its resources and dependency checks.
- Pin chart dependencies. Keep `Chart.yaml`, `Chart.lock` and vendored charts in sync.

## Runtime and configuration

- Use `repository:tag@sha256:<digest>` for images, including init containers and tools. Do not add a version comment.
- Use one application image for its web processes, workers and migrations. Put the image setting at application level.
- Set CPU and memory requests and limits for every container.
- Set an explicit non-root user and group. Disable privilege escalation and drop all capabilities.
- Use a read-only root filesystem. Mount writable paths on volumes with suitable ownership. Bound temporary storage.
- Give long-running containers readiness and liveness probes, including workers. Require the app's actual health paths and ports.
- Check startup dependencies with bounded init-container checks, such as `common.network.hostcheck`. Use stable names and fail on timeout.
- Store secret names and key references in values, not secret contents. Mount only needed secret files, read-only, with restricted permissions.
- Put non-secret settings in ConfigMaps. Share env helpers between an app and its Jobs. Avoid accidental overrides between `envFrom` and `env`.
- Define referenced env variables before values that use `$(VAR)`.
- Wire the right ServiceAccount and image pull secrets into workloads and Jobs.

## Migrations and hooks

- Run schema migrations as `pre-install,pre-upgrade` Jobs. New code must not start on the old schema. Schema changes must work with old code still running.
- Run data migrations as `post-install,post-upgrade` Jobs after the new code is ready.
- Use `restartPolicy: Never` and `backoffLimit: 0` for migration Jobs. Fail the release when they fail.
- Set `helm.sh/hook-delete-policy: before-hook-creation`. Keep failed runs available for inspection.
- Use hook weights to order dependencies within each phase. Create prerequisites before preparation Jobs, then migrations. Do not rely on equal weights for ordering.
- Make every pre-install hook dependency available before normal release resources are created.
- Keep costly tasks such as search reindexing opt-in.

## Availability

- Use `RollingUpdate` with `maxSurge: 0` and `maxUnavailable: 1`. Plan for one fewer available replica during rollout; a single replica can cause downtime.
- Add a PDB for workloads with multiple replicas. Use `maxUnavailable: 1` and the workload's selector. Account for the HPA minimum.
- Use worker HPA with explicit replica bounds, CPU targets and stabilization windows. Limit scaling steps to avoid sudden worker churn.
- Omit Deployment `replicas` when HPA controls the count.
- Give user-facing services and release hooks higher priority than background workers.
- Support existing PriorityClasses. Make cluster-scoped creation opt-in. Set `globalDefault: false` and an explicit preemption policy.
- Default `maintenance` to `false`. When enabled, route public app traffic to a maintenance page returning HTTP 503. Keep its health endpoint working.

## Development and releases

- Default `mode` to `prod`. Allow `mode: dev` only for a Skaffold code-sync loop. Disable only probes and `readOnlyRootFilesystem` when they block code sync.
- Use Skaffold only for development on a shared dev cluster.
- Test every chart change on local kind.
- Promote normal releases through qa → beta → prod with reviewed PRs.
- Resolve image digests during version updates. Promote tested chart code and exact image versions without rebuilding. Preserve environment settings.
- Keep previews tied to their source work. Update them with chart changes and remove them when that work closes.
- Document values with `# --` comments. Generate their documentation with helm-docs in pre-commit.

## Validation

1. Run `helm template` on the changed chart with appropriate values
2. Check ALL required args, env vars, and volume mounts are present
3. Verify no duplicate keys exist
4. Report all errors at once, not one at a time

### Automated checks

- Run the same checks locally and in CI for every supported environment. Supply required preview values explicitly.
- Run yamllint with `key-duplicates` on values files and rendered YAML.
- Check vendored dependencies with `helm dependency list`. Every dependency must report `ok`.
- Run `helm lint` with each environment's values. Keep `values.schema.json` in sync with supported keys, types and required inputs.
- Validate rendered manifests with kubeconform. Include schemas for the CRDs the chart uses. Treat missing schemas as a validation gap.
- Encode chart rules as Rego `deny` policies and run them with conftest against rendered manifests.
- Cover resources, security contexts, probes, image references, labels, selectors, hook phases, retry settings, routing, env sources and secret mounts.
- Apply policies to init containers and Jobs as well as app containers. Keep exceptions explicit and narrow.
- Make policies enforce this skill's rules. Do not copy conflicting rules from another chart.
- Test policy changes with valid and invalid manifests. Check that each rule rejects its intended violation.
- Fail CI on render, schema or policy errors. Preserve failures through shell pipelines and collect results across environments.
- Recheck affected charts when shared helpers, dependencies or policies change.
