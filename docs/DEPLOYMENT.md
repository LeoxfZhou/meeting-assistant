# Deployment Validation

## Verified environment

Ubuntu24.04.5 ECS,2vCPU/2GiB RAM,2GiB persistent Swap; Docker29.1.3 and Compose2.40.3. FastAPI and PostgreSQL16/pgvector containers were healthy; Alembic reached0004_knowledge. The deployment used reviewed source archives and official-source amd64 images transferred over SSH. No GitHub credentials or development .env were copied to the server.

API memory limit900MiB; PostgreSQL450MiB, shared_buffers64MB and max_connections30. API8000 and PostgreSQL55432 were bound to loopback; onlySSH was exposed. SSH key login and tunnel access were verified.

## Persistence and recovery

A synthetic meeting survived container restart and full ECS reboot. Docker was enabled at boot and persistent Swap returned. Compose down without -v removed containers/network while retaining the PostgreSQL named volume; up restored the same meeting and CPU vector retrieval.

## Generation scope

Real LLM calls were validated on the development Mac. Mainland ECS could not establish a direct connection to api.openai.com:443; no HTTP status was received, so this was not diagnosed as a credential or quota error. Cloud validation covered infrastructure rather than a permanent public service.

## Intentional decommission

After evidence preservation, the demo-only database was checked: one synthetic user, one synthetic meeting, no tasks or candidates. Authorized compose down -v removed project containers/network/volume. /opt/meeting-assistant, its .env/model copy and dedicated probes were removed. A new SSH connection confirmed Docker/Compose and Swap remained available. Ubuntu,Git,SSH configuration and authorized keys were retained. No global prune or operating-system reinstall was performed.

There is no currently running public Meeting Assistant service. [Machine-readable lifecycle evidence](../evaluation/evidence/cloud_validation.json).

## Reproduction

Use docker-compose.yml and, for constrained hosts, compose.cloud.yml after setting its image tag to a locally built image. Create host-specific credentials from .env.example. Keep database ports private. API startup runs Alembic before Uvicorn. Validate health, authenticated CRUD, retrieval and persistent data after restart; /health alone is only liveness.

Named volumes survive stop/restart and down without -v. Only use down -v when permanent data removal is intended. A changed POSTGRES_PASSWORD environment variable does not update the password inside an existing database. Do not reuse development credentials in another environment.
