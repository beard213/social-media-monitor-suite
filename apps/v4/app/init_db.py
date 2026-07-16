from sqlalchemy import select
from app.db.session import engine, Base, SessionLocal
from app.db import models  # noqa
from app.db.models import MonitorTask, TaskProfile


def main():
    Base.metadata.create_all(engine)
    backfilled = 0
    with SessionLocal() as db:
        tasks = db.scalars(select(MonitorTask)).all()
        for task in tasks:
            if task.profile is None:
                task.profile = TaskProfile(
                    topic_template="custom",
                    regions=["nationwide"],
                    collect_comments=True,
                    expand_related=True,
                    auto_audit=True,
                )
                backfilled += 1
        db.commit()
    print(f"database initialized; task profiles backfilled={backfilled}")


if __name__ == "__main__":
    main()
