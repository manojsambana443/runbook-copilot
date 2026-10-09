# ImagePullBackOff / ErrImagePull

## Symptoms
New pods stay in `ImagePullBackOff` after a deploy. Events show `unauthorized`, `401`, `manifest unknown` or `not found` while pulling from the container registry.

## Diagnosis
Check the image name and tag in the deployment. Confirm the tag exists in Azure Container Registry. If the tag exists, verify the cluster can authenticate: the AKS kubelet identity needs the AcrPull role, or the pull secret must be present and not expired.

## Resolution
Fix the image tag if it is wrong, or re-attach the registry pull credentials or AcrPull role, then redeploy. Confirm pods reach Running.

Approved fix: FIX-004.
