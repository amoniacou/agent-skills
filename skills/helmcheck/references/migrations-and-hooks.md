# Migrations and Hooks

## Schema migration Job

- This example uses the [shared Rails container](shared-containers.md) and its backend values.
- Supply the chart's ServiceAccount and pull secrets where needed. Add bounded checks for the Job's actual network dependencies.

```gotemplate
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "common.names.fullname" . }}-schema-migration
  labels:
    {{- include "common.labels.standard" . | nindent 4 }}
    tier: schema-migration
  annotations:
    helm.sh/hook: pre-install,pre-upgrade
    helm.sh/hook-weight: "-1"
    helm.sh/hook-delete-policy: before-hook-creation
spec:
  backoffLimit: 0
  template:
    metadata:
      labels:
        {{- include "common.labels.standard" . | nindent 8 }}
        tier: schema-migration
    spec:
      restartPolicy: Never
      securityContext:
        runAsNonRoot: true
        fsGroup: 10001
      containers:
        - {{- include "app.railsContainer" (dict
              "app" .Values.backend "role" "schemaMigration" "mode" .Values.mode
            ) | nindent 10 }}
      volumes:
        - name: rails-cache-volume
          emptyDir:
            sizeLimit: 500Mi
```

## Data migration Job

- Use the same Job structure with the following substitutions:

| Field | Schema Job | Data Job |
| --- | --- | --- |
| Name suffix and `tier` | `schema-migration` | `data-migration` |
| `helm.sh/hook` | `pre-install,pre-upgrade` | `post-install,post-upgrade` |
| Container helper role | `schemaMigration` | `dataMigration` |

- Both Jobs read `backend.image` from the new release values. The old Puma and Sidekiq pods may still run during the schema Job.
- Example compatible change: add a nullable column first. Remove the old column only after no running code needs it.
- Enable the deploy tool's readiness wait before post hooks. Their phase alone does not wait for healthy new workloads.

## Weight example

| Resource or task | Phase | Weight |
| --- | --- | --- |
| PriorityClass | pre-install, pre-upgrade | `-100` |
| Dev dependency preparation | pre-install | `-5` |
| Schema migration | pre-install, pre-upgrade | `-1` |
| Data migration | post-install, post-upgrade | `-1` |

- The two migration weights can match because their phases differ.
- If a separate check must finish before a migration, give it a lower weight or make it a bounded init container in that Job.
- The example's ConfigMap and Secret are external. A chart-managed replacement needs its own earlier hook phase and weight.
- A dev preparation Job that needs a PVC cannot rely on an ordinary PVC from the same first install.

## Failure checks

- Force a schema Job failure and check that new app workloads do not start.
- Force a data Job failure and check that the release reports failure after the new app has started.
- Inspect the failed Job's logs before retrying. Check that the next hook run replaces the previous Job.
- A failed release does not undo database changes. Include that case when checking migration compatibility.
