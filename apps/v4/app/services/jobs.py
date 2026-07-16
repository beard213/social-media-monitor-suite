from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Job
from app.utils import utcnow


def enqueue(db: Session, job_type: str, payload: dict, max_attempts: int = 3):
    job = Job(job_type=job_type, payload=payload, max_attempts=max_attempts)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def claim(db: Session):
    query = (
        select(Job)
        .where(Job.status == "pending", Job.run_after <= utcnow())
        .order_by(Job.created_at)
        .limit(1)
    )
    # PostgreSQL workers can safely claim different rows concurrently. SQLite is
    # intended for one local worker and does not support SKIP LOCKED.
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        query = query.with_for_update(skip_locked=True)
    job = db.scalar(query)
    if not job:
        return None
    job.status = "running"
    job.locked_at = utcnow()
    job.attempts += 1
    db.commit()
    db.refresh(job)
    return job


def fail(db: Session, job: Job, error: str):
    job.last_error = error
    if job.attempts >= job.max_attempts:
        job.status = "failed"
    else:
        job.status = "pending"
        job.run_after = utcnow() + timedelta(seconds=min(300, 2**job.attempts * 5))
    db.commit()


def done(db: Session, job: Job):
    job.status = "success"
    job.last_error = ""
    db.commit()
