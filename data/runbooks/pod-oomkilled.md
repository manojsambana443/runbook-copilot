# Container killed with OOMKilled

## Symptoms
A container restarts repeatedly. `kubectl describe pod` shows `Last State: Terminated, Reason: OOMKilled` and exit code 137. Memory usage climbs to the limit before each restart.

## Diagnosis
Compare the memory limit in the Helm values with the working-set memory in Grafana. For Java services, check that the heap size is lower than the container limit. Look for a leak if memory grows steadily without traffic growth.

## Resolution
Raise the memory request and limit for the container in the Helm values and redeploy. Watch memory for thirty minutes. If memory keeps growing, open a defect for a leak.

Approved fix: FIX-002.
