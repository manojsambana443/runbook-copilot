# 5xx spike after a release

## Symptoms
The error rate jumps from under 1% to a sustained spike right after a deployment. Errors affect endpoints changed in the release. The previous version was healthy.

## Diagnosis
Correlate the start of the spike with the deploy time in Grafana. Check the release notes and the diff, and confirm the errors are application errors rather than infrastructure (compare with node and database health).

## Resolution
Roll back to the last known good release with `helm rollback` or by redeploying the previous image tag. Confirm the error rate returns to baseline and open a defect before attempting the release again.

Approved fix: FIX-009.
