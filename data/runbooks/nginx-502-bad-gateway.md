# Nginx 502 Bad Gateway

## Symptoms
Users receive `502 Bad Gateway`. The Nginx error log shows `upstream prematurely closed connection`, `connect() failed` or `no live upstreams`.

## Diagnosis
Check that the upstream service is running and listening on the port in the Nginx config. Compare the upstream address with the current service address after any redeploy. Run `nginx -t` to validate the configuration and review health-check settings and timeouts.

## Resolution
Correct the upstream target or health check, validate with `nginx -t`, then reload Nginx. Confirm 502s stop in the access log.

Approved fix: FIX-010.
