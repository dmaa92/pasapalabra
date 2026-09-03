# Deploying

The application is a single stateless container image. Anything that can
run an OCI image can run it; these manifests are the Kubernetes flavour
of the same thing `docker-compose.yml` does locally.

## Any container platform

```
docker build -t pasapalabra:1 .
docker run --rm -p 8080:8000 --read-only --tmpfs /tmp pasapalabra:1
```

The container listens on `8000`, serves the board on `/`, the judge panel
on `/juez`, the API under `/api/`, and a liveness endpoint on `/healthz`.
It needs no database, no volume, and no environment variable to start.

For a refereed match the judge's device has to reach the same origin as
the board — one hostname or IP that both can open is the whole
requirement.

## Kubernetes

```
kubectl create namespace pasapalabra
kubectl -n pasapalabra apply -f deploy/k8s/
kubectl -n pasapalabra port-forward svc/pasapalabra 8080:80
```

Set a real image tag in `deployment.yaml` first — `REPLACE_ME` is not a
tag, deliberately, so an unedited manifest fails loudly instead of
deploying something unexpected.

Exposure (Ingress, LoadBalancer, tunnel) is left out on purpose: it is
an environment-specific decision, not a property of the app.
