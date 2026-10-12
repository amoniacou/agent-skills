# Shared Containers

## When to extract

- Several Rails services repeat the same commands, env wiring, mounts and runtime settings. A shared container helper keeps that setup in one place.
- Share the Rails setup across apps. Keep each app's Deployments, Jobs, Services and scheduling visible in its templates.
- Keep a service with a different runtime in its own template. Do not grow the Rails helper into a general Kubernetes object builder.

## One chart, several apps

```text
charts/
  common/
    templates/
      _ruby.tpl
templates/
  backend/
    puma-deployment.yaml
    sidekiq-deployment.yaml
    schema-migration.yaml
    data-migration.yaml
    service.yaml
  auth/
    puma-deployment.yaml
    service.yaml
```

- Example values for one app. Replace `<digest>` with its digest. The ConfigMap and Secret already exist so pre-install Jobs can read them.

```yaml
mode: prod
backend:
  image: "backend:1.4.0@sha256:<digest>"
  existingConfigMap: backend-config
  existingSecret: backend-env
  puma:
    replicaCount: 3
    cpu: "1000m"
    memory: "1Gi"
    healthPort: 9393
    readinessPath: "/checks/readiness"
    livenessPath: "/checks/liveness"
  sidekiq:
    replicaCount: 2
    cpu: "500m"
    memory: "1Gi"
    healthPort: 7433
    readinessPath: "/ready"
    livenessPath: "/live"
  schemaMigration:
    cpu: "500m"
    memory: "512Mi"
  dataMigration:
    cpu: "1000m"
    memory: "2Gi"
```

## Shared helper

- Example replacement for `common.ruby.common` in the library's `_ruby.tpl`. It returns one container map.
- Update library callers and pin the new dependency version together. This interface differs from the older helper that returns a container list.
- Fix shared runtime rules in the library. Do not patch its rendered output in an application helper.

```gotemplate
{{- define "common.ruby.common" -}}
{{- $commands := dict
  "puma" (list "bundle" "exec" "puma")
  "sidekiq" (list "bundle" "exec" "sidekiq")
  "schemaMigration" (list "bundle" "exec" "rails" "db:migrate")
  "dataMigration" (list "bundle" "exec" "rake" "data:migrate")
-}}
{{- if not (hasKey $commands .role) -}}
  {{- fail (printf "unknown Rails role: %s" .role) -}}
{{- end -}}
{{- $settings := required (printf "%s settings are required" .role) (index .app .role) -}}
{{- $mode := .mode | default "prod" -}}
{{- if not (has $mode (list "prod" "dev")) -}}
  {{- fail "mode must be prod or dev" -}}
{{- end -}}
{{- $envFrom := list
  (dict "configMapRef" (dict "name" (required "app.existingConfigMap is required" .app.existingConfigMap)))
  (dict "secretRef" (dict "name" (required "app.existingSecret is required" .app.existingSecret)))
-}}
{{- $resources := dict
  "cpu" (required (printf "%s.cpu is required" .role) $settings.cpu)
  "memory" (required (printf "%s.memory is required" .role) $settings.memory)
-}}
{{- $base := dict
  "name" (.role | kebabcase)
  "image" (required "app.image is required" .app.image)
  "imagePullPolicy" "IfNotPresent"
  "args" (index $commands .role)
  "envFrom" $envFrom
  "resources" (dict "requests" (deepCopy $resources) "limits" (deepCopy $resources))
  "securityContext" (dict
    "runAsUser" 10001
    "runAsGroup" 10001
    "runAsNonRoot" true
    "allowPrivilegeEscalation" false
    "readOnlyRootFilesystem" true
    "capabilities" (dict "drop" (list "ALL"))
  )
  "volumeMounts" (list (dict "name" "rails-cache-volume" "mountPath" "/tmp"))
-}}
{{- if has .role (list "puma" "sidekiq") -}}
  {{- $port := required (printf "%s.healthPort is required" .role) $settings.healthPort -}}
  {{- range $probe, $key := dict "readinessProbe" "readinessPath" "livenessProbe" "livenessPath" -}}
    {{- $path := required (printf "%s.%s is required" $.role $key) (index $settings $key) -}}
    {{- $_ := set $base $probe (dict
      "httpGet" (dict "path" $path "port" $port)
      "periodSeconds" 10
      "timeoutSeconds" 3
      "failureThreshold" 3
    ) -}}
  {{- end -}}
{{- end -}}
{{- $container := mergeOverwrite (deepCopy $base) (.extra | default dict) -}}
{{- if eq $mode "dev" -}}
  {{- $container = omit $container "readinessProbe" "livenessProbe" -}}
  {{- $_ := unset $container.securityContext "readOnlyRootFilesystem" -}}
{{- end -}}
{{- toYaml $container -}}
{{- end -}}
```

## Workload templates

- Backend Puma: put this fragment in the Deployment's `spec.template.spec`.

```gotemplate
containers:
  - {{- include "common.ruby.common" (dict
        "app" .Values.backend "role" "puma" "mode" .Values.mode
      ) | nindent 4 }}
```

- Backend Sidekiq uses the same app values:

```gotemplate
containers:
  - {{- include "common.ruby.common" (dict
        "app" .Values.backend "role" "sidekiq" "mode" .Values.mode
      ) | nindent 4 }}
```

- The schema and data Jobs pass `schemaMigration` and `dataMigration`. See [migration templates](migrations-and-hooks.md).
- The auth Deployment passes `"app" .Values.auth` and `"role" "puma"`. Its values supply another image, config references and Puma settings.
- Each Pod supplies `rails-cache-volume` as a bounded `emptyDir` for `/tmp`, with `fsGroup: 10001`.

## Native Kubernetes tuning

- Example block in the backend template:

```gotemplate
{{- define "app.backendPumaFields" -}}
readinessProbe:
  timeoutSeconds: 5
securityContext:
  seccompProfile:
    type: RuntimeDefault
{{- end -}}
```

- Pass its parsed map as `extra`:

```gotemplate
containers:
  - {{- include "common.ruby.common" (dict
        "app" .Values.backend "role" "puma" "mode" .Values.mode
        "extra" (include "app.backendPumaFields" . | fromYaml)
      ) | nindent 4 }}
```

- Probe timing and seccomp stay native Kubernetes fields. Adding either needs no new helper parameter.
- Maps merge; lists replace. A `volumeMounts` override must include the existing mounts.
- Run [policy checks](validation.md) against the merged container. Tuning must preserve the runtime requirements.
