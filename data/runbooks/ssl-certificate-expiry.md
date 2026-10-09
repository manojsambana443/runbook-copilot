# TLS certificate expired or expiring

## Symptoms
Browsers show a certificate expired or "connection not private" warning. API clients fail with `certificate has expired`. Monitoring warns that a certificate expires within 14 days.

## Diagnosis
Check the expiry with `openssl s_client -connect host:443 | openssl x509 -noout -dates`. Confirm whether auto-renewal failed (certbot timer, Key Vault rotation policy) and which certificate the proxy is actually serving.

## Resolution
Renew the certificate through Key Vault or certbot, deploy the new certificate, and reload Nginx. Verify the new expiry date from outside the network and fix the renewal job.

Approved fix: FIX-007.
