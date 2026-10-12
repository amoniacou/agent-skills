# Availability

## Worker HPA

- Example `autoscaling/v2` HPA `spec` for a Sidekiq Deployment:

```yaml
scaleTargetRef:
  apiVersion: apps/v1
  kind: Deployment
  name: app-sidekiq
minReplicas: 2
maxReplicas: 6
metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
behavior:
  scaleUp:
    stabilizationWindowSeconds: 300
    policies:
      - type: Pods
        value: 1
        periodSeconds: 180
  scaleDown:
    stabilizationWindowSeconds: 600
    policies:
      - type: Pods
        value: 1
        periodSeconds: 300
```

- Match `scaleTargetRef.name` to the rendered Deployment. Tune the example numbers against worker load and job duration.
- Example replica field in the worker Deployment:

```gotemplate
{{- if not .Values.backend.sidekiq.autoscaling.enabled }}
replicas: {{ .Values.backend.sidekiq.replicaCount }}
{{- end }}
```

## Matching PDB

- Example `policy/v1` PDB `spec` for the same worker:

```yaml
maxUnavailable: 1
selector:
  matchLabels:
    app.kubernetes.io/name: app
    app.kubernetes.io/instance: example
    tier: sidekiq
```

- In templates, replace these literal labels with the same selector helper used by the Deployment.
- Use `minReplicas` when HPA is enabled and `replicaCount` otherwise to decide whether this workload has multiple replicas.
- With a minimum of two healthy pods, this budget permits one voluntary disruption. With one pod, it permits losing that pod.
- PDB controls voluntary disruptions. Check the Deployment's rollout strategy separately.

## PriorityClass

- Example values for optional class creation:

```yaml
priorityClass:
  create: false
  high:
    name: ""
    value: 1000000
    preemptionPolicy: PreemptLowerPriority
  low:
    name: ""
    value: 100000
    preemptionPolicy: PreemptLowerPriority
```

- Name resolution: use the explicit name; otherwise generate a release-scoped name when `create` is true; otherwise omit `priorityClassName`.
- A created class has `globalDefault: false` and no namespace. Its creation needs cluster-level RBAC.
- Assign `high` to serving workloads and release Jobs; assign `low` to background workers.
- Create classes before Jobs that reference them. See [hook weights](migrations-and-hooks.md#weight-example).

## Maintenance routing

- Example backend selection inside each public ingress path:

```gotemplate
backend:
  service:
    name: {{ include "common.names.fullname" . }}-{{ ternary "maintenance" "frontend" .Values.maintenance }}
    port:
      number: 8080
```

- Replace `frontend` with that path's normal backend. Apply the switch to every public app host and path, including API and auth routes.
- Create the maintenance Deployment, Service and ConfigMap under the same switch. Keep app workloads running.
- Example nginx server:

```nginx
server {
    listen 8080;
    location = /healthz {
        return 200 "ok";
    }
    location / {
        default_type text/html;
        return 503 "<h1>Maintenance</h1>";
    }
}
```

- Expose the maintenance Service on port 8080, the same as the container. Use `/healthz` on 8080 for probes.
- Check that public requests return 503, the maintenance pod stays ready, and disabling maintenance restores each original backend.
