# ExamFlow ingress and egress setup

The application uses NGINX Ingress with two hostnames:

- `admin.examflow.local` for the admin UI
- `scanner.examflow.local` for the scanner UI

`kind-lan.yml` publishes the ingress controller's HTTP and HTTPS NodePorts on
the host's ports 80 and 443. Recreate the Kind cluster with that configuration:

```bash
kind delete cluster
kind create cluster --config kind-lan.yml
```

Because Kind nodes do not automatically use Docker images built on the host,
load the application images into the new cluster before deploying:

```bash
kind load docker-image examflow-backend:1.0.0 \
  examflow-admin-ui:1.0.0 \
  examflow-scanner-ui:1.0.0 \
  --name kind
```

Install the NGINX Ingress Controller before applying `ingress.yml`:

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --values kubernetes/ingress-nginx-values.yml
```

Apply the application manifests and the ingress and network policies. Do not
apply `port-forwarder.yml`; it is an old Kind configuration file, not a
Kubernetes resource:

```bash
kubectl apply -f kubernetes/namespace.yml
kubectl apply -f kubernetes/backend-configmap.yml \
  -f kubernetes/backend-deployment.yml \
  -f kubernetes/backend-service.yml \
  -f kubernetes/frondend-service.yml \
  -f kubernetes/frontend-configmap.yml \
  -f kubernetes/frontend-deployment.yml \
  -f kubernetes/postgres-deployment.yml \
  -f kubernetes/postgres-pvc.yml \
  -f kubernetes/postgres-secret.yml \
  -f kubernetes/postgres-service.yml \
  -f kubernetes/ingress.yml \
  -f kubernetes/network-policy.yml
```

For local-network DNS, add these entries on every client computer, or create
the equivalent records in the LAN DNS server:

```text
10.129.2.182 admin.examflow.local scanner.examflow.local
```

Then browse to `http://admin.examflow.local` or
`http://scanner.examflow.local`.

`network-policy.yml` applies least-privilege ingress and egress rules. The
backend may reach PostgreSQL, DNS, and SMTP over TCP 465. The frontend pods may
reach the backend and DNS. NetworkPolicy enforcement requires a compatible CNI
such as Calico or Cilium; Kind's default networking may not enforce the rules.
