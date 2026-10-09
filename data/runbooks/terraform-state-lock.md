# Terraform state lock error

## Symptoms
`terraform plan` or `apply` fails with `Error acquiring the state lock`. The message shows a lock ID, who holds it, and when it was created. A pipeline run was cancelled or crashed earlier.

## Diagnosis
Check the CI system for a running job that could legitimately hold the lock. Read the lock metadata (operation, user, timestamp). If the holder run no longer exists, the lock is stale. Never unlock while a run is active.

## Resolution
Once you confirm that no run is active, release the lock with `terraform force-unlock <LOCK_ID>`, then re-run the pipeline. Record the incident.

Approved fix: FIX-008.
