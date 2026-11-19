# Infra notes
- One server: <host> (IP <server-ip>), Docker Compose, nightly encrypted backups.
- Model: hosted LLM API, no patient data used for training (contract clause).
- Staging on the same box with fake patients. Deploys by GitHub Actions after review.
- Open: second server for failover (not started).
