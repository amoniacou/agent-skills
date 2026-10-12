# Deployments

## HTTP service values

- This example serves requests and health checks on the same port.
- It uses `common.names.*` and `common.labels.*` from the chart's library dependency.
- Replace `<digest>` with the image digest. The named ServiceAccount, ConfigMap and Secret must exist in the release namespace.

```yaml
mode: prod
imagePullSecrets: []
serviceAccount:
  name: app-runtime
nodeSelector: {}
affinity: {}
tolerations: []
app:
  image: "app:1.4.0@sha256:<digest>"
  replicaCount: 2
  autoscaling:
    enabled: false
  priorityClassName: ""
  port: 8080
  readinessPath: "/ready"
  livenessPath: "/live"
  existingConfigMap: app-config
  existingSecret: app-env
  resources:
    requests:
      cpu: "250m"
      memory: "256Mi"
    limits:
      cpu: "1000m"
      memory: "512Mi"
```

## Deployment template

```gotemplate
{{- $mode := .Values.mode | default "prod" -}}
{{- if not (has $mode (list "prod" "dev")) -}}
  {{- fail "mode must be prod or dev" -}}
{{- end }}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "common.names.fullname" . }}-app
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "common.labels.standard" . | nindent 4 }}
    tier: app
spec:
  {{- if not .Values.app.autoscaling.enabled }}
  replicas: {{ .Values.app.replicaCount }}
  {{- end }}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 0
  selector:
    matchLabels:
      {{- include "common.labels.matchLabels" . | nindent 6 }}
      tier: app
  template:
    metadata:
      labels:
        {{- include "common.labels.standard" . | nindent 8 }}
        tier: app
    spec:
      serviceAccountName: {{ required "serviceAccount.name is required" .Values.serviceAccount.name | quote }}
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.app.priorityClassName }}
      priorityClassName: {{ . | quote }}
      {{- end }}
      securityContext:
        runAsNonRoot: true
        fsGroup: 10001
        fsGroupChangePolicy: OnRootMismatch
        seccompProfile:
          type: RuntimeDefault
      terminationGracePeriodSeconds: 60
      containers:
        - name: app
          image: {{ required "app.image is required" .Values.app.image | quote }}
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: {{ required "app.port is required" .Values.app.port }}
          securityContext:
            runAsUser: 10001
            runAsGroup: 10001
            runAsNonRoot: true
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
            {{- if eq $mode "prod" }}
            readOnlyRootFilesystem: true
            {{- end }}
          envFrom:
            - configMapRef:
                name: {{ required "app.existingConfigMap is required" .Values.app.existingConfigMap | quote }}
            - secretRef:
                name: {{ required "app.existingSecret is required" .Values.app.existingSecret | quote }}
          {{- if eq $mode "prod" }}
          readinessProbe:
            httpGet:
              path: {{ required "app.readinessPath is required" .Values.app.readinessPath | quote }}
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
          livenessProbe:
            httpGet:
              path: {{ required "app.livenessPath is required" .Values.app.livenessPath | quote }}
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 3
          {{- end }}
          resources:
            {{- required "app.resources is required" .Values.app.resources | toYaml | nindent 12 }}
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir:
            sizeLimit: 256Mi
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.affinity }}
      affinity:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
```

## Matching Service

```gotemplate
apiVersion: v1
kind: Service
metadata:
  name: {{ include "common.names.fullname" . }}-app
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "common.labels.standard" . | nindent 4 }}
    tier: app
spec:
  type: ClusterIP
  selector:
    {{- include "common.labels.matchLabels" . | nindent 4 }}
    tier: app
  ports:
    - name: http
      port: 80
      targetPort: http
```

## Adapt the example

- For another service, use its own values block, resource suffix and `tier` consistently in the Deployment and Service.
- The image supplies the process entrypoint here. Add native `command` or `args` when the workload needs another process.
- For a worker, keep the Deployment structure and working probes. Omit the Service unless another workload calls it.
- If autoscaling is enabled, supply an HPA targeting this Deployment. See [worker HPA and PDB](availability.md).
- For repeated Rails containers, replace only the container block with the [shared helper](shared-containers.md). Keep the Deployment structure here.
- Check that every Deployment and Service selector matches the pod labels, every probe port resolves, and every mount has a volume.
