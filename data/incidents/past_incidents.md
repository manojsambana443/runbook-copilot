# Past incidents

## INC-1041: Checkout latency during a sale
CPU on the checkout pods stayed above 90% as traffic tripled. The HPA had reached its maximum of 4 replicas. Raising the HPA ceiling to 10 brought latency back to normal in eight minutes. Runbook: runbooks/aks-pod-high-cpu.md.

## INC-1058: Orders service restarting every few minutes
The orders container was OOMKilled (exit code 137). The memory limit was 512Mi against a working set of 700Mi. Raising the limit to 1Gi stopped the restarts. Runbook: runbooks/pod-oomkilled.md.

## INC-1073: Deploy blocked by registry authentication
New pods hit ImagePullBackOff with a 401 error after the cluster was recreated. The AcrPull role had not been assigned to the new kubelet identity. Assigning it and redeploying fixed it. Runbook: runbooks/imagepullbackoff.md.

## INC-1090: Database refused new connections
Applications logged "Too many connections" after autoscaling doubled the replica count. Each pod used a pool of 50, which exceeded max_connections. Cutting the pool to 15 and restarting leaking pods resolved it. Runbook: runbooks/mysql-too-many-connections.md.

## INC-1102: Build agent out of disk
A build VM filled /var with old container images and logs. Pruning images and compressing logs freed 40 GB. Log rotation was added afterwards. Runbook: runbooks/vm-disk-full.md.

## INC-1115: Error spike after release 2.4
The 5xx rate rose to 12% right after release 2.4. A rollback to 2.3 restored normal error rates within five minutes. Runbook: runbooks/bad-release-5xx-spike.md.
