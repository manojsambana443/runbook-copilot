# CrashLoopBackOff because a dependency was not ready

## Symptoms
A pod restarts in a loop right after deploy or after a dependency outage. Logs at startup show `connection refused` to the database, cache or message queue. The dependency is healthy again now.

## Diagnosis
Read the previous container's logs with `kubectl logs --previous`. Confirm the dependency is reachable now from inside the cluster, and that the configuration (host, port, credentials) is correct. If the config is wrong, fix the config first.

## Resolution
Once dependencies are healthy and the configuration is correct, do a rolling restart of the deployment so pods start cleanly. Add a readiness check or startup retry to prevent a repeat.

Approved fix: FIX-001.
