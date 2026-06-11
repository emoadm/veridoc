"""RQ worker entrypoint for the ingestion-service.

Run via:

    rq worker ingestion --serializer rq.serializers.JSONSerializer --url $VERIDOC_REDIS_URL

Or via the module entrypoint (used in the Kubernetes worker Deployment):

    python -m ingestion_service.worker_main

The worker consumes jobs from the ``"ingestion"`` queue enqueued by
POST /ingest/{site_id}.  JSONSerializer is mandatory — pickle is an RCE vector
(Pitfall 3, T-02-SVC-03).

Analog: ``services/reference-service/src/reference_service/migrate.py``
(module-level entrypoint / path-setup pattern).
"""

from __future__ import annotations

from redis import Redis
from rq import Worker
from rq.serializers import JSONSerializer

from .config import get_settings


def main() -> None:
    """Start the RQ worker on the ``"ingestion"`` queue with JSONSerializer."""
    settings = get_settings()
    conn = Redis.from_url(settings.redis_url)
    # JSONSerializer is REQUIRED (Pitfall 3 / T-02-SVC-03: no pickle RCE)
    worker = Worker(["ingestion"], connection=conn, serializer=JSONSerializer)
    worker.work()


if __name__ == "__main__":
    main()
