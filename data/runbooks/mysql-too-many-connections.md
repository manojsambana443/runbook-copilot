# MySQL "Too many connections"

## Symptoms
Applications log `ERROR 1040: Too many connections` or connection pool timeouts. New requests hang while existing ones work. Active connections sit near `max_connections`.

## Diagnosis
Run `SHOW PROCESSLIST` and `SHOW STATUS LIKE 'Threads_connected'`. Group by user and host to find the service holding the most connections. Multiply pool size by replica count: autoscaling often pushes the total over the limit. Look for idle connections that are never released.

## Resolution
Reduce the per-pod pool size, restart pods that leak connections, and raise `max_connections` within the approved range for the server size. Confirm connections settle below 80% of the limit.

Approved fix: FIX-005.
