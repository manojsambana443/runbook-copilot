# Disk full on a Linux VM

## Symptoms
Writes fail with `No space left on device`. Builds fail, services crash, or the database stops accepting writes. `df -h` shows a volume at 95-100%.

## Diagnosis
Run `df -h` then `du -xh /var --max-depth=2 | sort -h | tail`. Common causes are large files in `/var/log`, unrotated application logs, old container images and layers, and temp files from failed builds.

## Resolution
Compress or rotate old logs, run `docker system prune` for unused images, and clear temp build directories. Never delete application or database data files. Confirm usage is under 80%, then add log rotation if it was missing.

Approved fix: FIX-006.
