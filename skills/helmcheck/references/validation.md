# Validation

## Run the checks

- Example Bash check. Arguments: chart directory, policy directory, then environment values files.
- Set `KUBERNETES_VERSION` to the target cluster version. Set `CRD_SCHEMA_LOCATION` to a schema path or URL template when the chart uses CRDs.
- Include preview inputs in a test values file. For layered values, extend all render commands with the same ordered `-f` arguments.

```bash
set -uo pipefail
chart="${1:?chart directory required}"
policy="${2:?policy directory required}"
shift 2
if [ "$#" -eq 0 ]; then
  echo "At least one environment values file is required" >&2
  exit 2
fi
: "${KUBERNETES_VERSION:?target Kubernetes version required}"
schema_args=(-schema-location default)
if [ -n "${CRD_SCHEMA_LOCATION:-}" ]; then
  schema_args+=(-schema-location "$CRD_SCHEMA_LOCATION")
fi

status=0
yaml_rules='{rules: {key-duplicates: enable}}'
yamllint -d "$yaml_rules" "$chart/values.yaml" "$@" || status=1
helm dependency list "$chart" |
  awk 'NR > 1 && NF > 0 && $NF != "ok" { print; bad = 1 } END { exit bad }' ||
  status=1
conftest verify --policy "$policy" || status=1

for values in "$@"; do
  printf 'Validating %s\n' "$values"
  helm lint "$chart" -f "$values" || status=1
  helm template validate "$chart" -f "$values" |
    yamllint -d "$yaml_rules" - || status=1
  helm template validate "$chart" -f "$values" |
    kubeconform -strict -summary \
      -kubernetes-version "$KUBERNETES_VERSION" \
      "${schema_args[@]}" || status=1
  helm template validate "$chart" -f "$values" |
    conftest test --policy "$policy" - || status=1
  helm template validate "$chart" -f "$values" |
    conftest test --combine --namespace services --policy "$policy" - || status=1
done
exit "$status"
```

- The script collects failures instead of stopping at the first environment. `pipefail` preserves a failed render even if the next tool accepts empty input.
- Do not add `-ignore-missing-schemas` to make CRD checks pass. Supply the missing schemas.
- The yamllint `key-duplicates` rule rejects repeated mapping keys before other tools can collapse them. Duplicate env names and mount paths need separate policy checks.

## Policy coverage

- Keep chart policies grouped by concern. Example groups:

| Group | Objects to inspect |
| --- | --- |
| Workloads | Every app and init container; resources, image and security fields |
| Health | Long-running containers, including workers without a declared port |
| Metadata | Resource labels, pod labels and matching selectors |
| Jobs | Migration phase, weight, restart policy and retry limit |
| Networking | Service targets, route hosts and backend ports |
| Configuration | Env sources, duplicate names and secret mounts |

- Feed dev-mode exceptions through explicit policy data tied to the render's values. Do not infer dev mode from a namespace or disable an entire policy group.
- Use a separate policy namespace for Skaffold configuration when the chart has a shared-cluster dev loop.
- To compare several resources, add a separate conftest pass with `--combine` and a policy written for its combined input shape.

## Example policy

- Example `policy/containers.rego`. It demonstrates container traversal and two rules, not the whole policy suite.

```rego
package main

import rego.v1

pod_spec := input.spec.template.spec if {
    input.kind in {"Deployment", "StatefulSet", "DaemonSet", "Job"}
}

pod_spec := input.spec.jobTemplate.spec.template.spec if {
    input.kind == "CronJob"
}

pod_spec := input.spec if input.kind == "Pod"

containers contains c if {
    some field in ["containers", "initContainers"]
    some c in object.get(pod_spec, field, [])
}

complete_resources(c) if {
    c.resources.requests.cpu
    c.resources.requests.memory
    c.resources.limits.cpu
    c.resources.limits.memory
}

deny contains msg if {
    some c in containers
    not complete_resources(c)
    msg := sprintf("%s/%s container %s: CPU and memory requests and limits are required",
        [input.kind, input.metadata.name, c.name])
}

deny contains msg if {
    some c in containers
    image := object.get(c, "image", "")
    not regex.match(`^.+:[A-Za-z0-9_][A-Za-z0-9_.-]*@sha256:[a-f0-9]{64}$`, image)
    msg := sprintf("%s/%s container %s: use repository:tag@sha256:digest",
        [input.kind, input.metadata.name, c.name])
}
```

## Policy tests

- Example `policy/containers_test.rego`. These fixtures isolate the policy; they are not complete Kubernetes manifests.

```rego
package main

import rego.v1

valid_container := {
    "name": "app",
    "image": "app:1.0.0@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "resources": {
        "requests": {"cpu": "100m", "memory": "128Mi"},
        "limits": {"cpu": "500m", "memory": "256Mi"},
    },
}

fixture := {
    "kind": "Deployment",
    "metadata": {"name": "example"},
    "spec": {"template": {"spec": {
        "containers": [valid_container],
        "initContainers": [object.union(valid_container, {"name": "db-check"})],
    }}},
}

test_valid_containers if {
    count(deny) == 0 with input as fixture
}

test_missing_init_memory_limit if {
    invalid := json.patch(fixture, [{
        "op": "remove",
        "path": "/spec/template/spec/initContainers/0/resources/limits/memory",
    }])
    failures := deny with input as invalid
    count(failures) == 1
    some msg in failures
    contains(msg, "container db-check: CPU and memory")
}

test_tag_without_digest if {
    invalid := json.patch(fixture, [{
        "op": "replace",
        "path": "/spec/template/spec/containers/0/image",
        "value": "app:1.0.0",
    }])
    failures := deny with input as invalid
    count(failures) == 1
    some msg in failures
    contains(msg, "container app: use repository:tag")
}
```

- Run `conftest verify --policy policy` after changing a rule or fixture.
- Extend fixtures with a second app container, a Job and a CronJob so traversal changes cannot silently drop coverage.
- For merge tuning, render one valid probe-timeout override and one invalid removal of a required field. Check that the valid change passes and the invalid one is rejected.
- For migrations, test schema and data phases separately. A Job with an unrelated Sync annotation must not satisfy the phase check.
- Keep expected failures specific to the resource, container and violated rule.

## Service port policy

- Example `policy/services.rego`. It runs in the `--combine` pass, so `input` is the list of rendered documents.

```rego
package services

import rego.v1

docs := [d.contents | some d in input]

selects(selector, labels) if {
    count(selector) > 0
    every k, v in selector {
        labels[k] == v
    }
}

container_ports(svc) := [p |
    some w in docs
    w.kind in {"Deployment", "StatefulSet", "DaemonSet"}
    object.get(w.metadata, "namespace", "") == object.get(svc.metadata, "namespace", "")
    selects(object.get(svc.spec, "selector", {}), object.get(w.spec.template.metadata, "labels", {}))
    some c in w.spec.template.spec.containers
    some p in object.get(c, "ports", [])
]

target_ports(svc, sp) := [p.containerPort |
    target := object.get(sp, "targetPort", sp.port)
    some p in container_ports(svc)
    target in {p.containerPort, object.get(p, "name", "")}
]

deny contains msg if {
    some svc in docs
    svc.kind == "Service"
    not svc.spec.selector.tier
    msg := sprintf("Service/%s: selector must include tier", [svc.metadata.name])
}

deny contains msg if {
    some svc in docs
    svc.kind == "Service"
    count(container_ports(svc)) > 0
    some sp in svc.spec.ports
    count(target_ports(svc, sp)) == 0
    msg := sprintf("Service/%s port %v: targetPort matches no container port",
        [svc.metadata.name, sp.port])
}

deny contains msg if {
    some svc in docs
    svc.kind == "Service"
    some sp in svc.spec.ports
    some n in target_ports(svc, sp)
    sp.port != n
    msg := sprintf("Service/%s port %v: must equal container port %v",
        [svc.metadata.name, sp.port, n])
}
```

- Example `policy/services_test.rego`:

```rego
package services

import rego.v1

deployment := {
    "kind": "Deployment",
    "metadata": {"name": "example-app"},
    "spec": {"template": {
        "metadata": {"labels": {"app": "example", "tier": "app"}},
        "spec": {"containers": [{
            "name": "app",
            "ports": [{"name": "http", "containerPort": 8080}],
        }]},
    }},
}

service := {
    "kind": "Service",
    "metadata": {"name": "example-app"},
    "spec": {
        "selector": {"app": "example", "tier": "app"},
        "ports": [{"name": "http", "port": 8080, "targetPort": "http"}],
    },
}

render(svc) := [
    {"path": "-", "contents": deployment},
    {"path": "-", "contents": svc},
]

test_matching_ports if {
    count(deny) == 0 with input as render(service)
}

test_service_port_80 if {
    invalid := json.patch(service, [{"op": "replace", "path": "/spec/ports/0/port", "value": 80}])
    failures := deny with input as render(invalid)
    count(failures) == 1
    some msg in failures
    contains(msg, "Service/example-app port 80: must equal container port 8080")
}

test_unknown_target_port if {
    invalid := json.patch(service, [{"op": "replace", "path": "/spec/ports/0/targetPort", "value": "web"}])
    failures := deny with input as render(invalid)
    count(failures) == 1
    some msg in failures
    contains(msg, "targetPort matches no container port")
}

test_selector_without_tier if {
    invalid := json.patch(service, [{"op": "remove", "path": "/spec/selector/tier"}])
    failures := deny with input as render(invalid)
    some msg in failures
    contains(msg, "Service/example-app: selector must include tier")
}
```
