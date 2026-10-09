# High CPU on AKS pods

## Symptoms
Pods run at 90%+ CPU for several minutes. Request latency climbs, queues build up, and the HPA reports it is at its maximum replica count.

## Diagnosis
Check `kubectl top pods -n <namespace>` and the HPA status with `kubectl get hpa`. Compare current replicas with the HPA maximum. Confirm the load increase is real traffic and not a runaway loop by looking at request rate in Grafana.

## Resolution
If traffic is legitimate, increase the replica count or raise the HPA maximum for the deployment. Verify CPU falls below 70% within ten minutes. If CPU stays high with flat traffic, escalate to the application team.

Approved fix: FIX-003.
