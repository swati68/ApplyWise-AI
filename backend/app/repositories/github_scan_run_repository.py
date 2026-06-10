from app.models.github_scan_run import GithubScanRun

from sqlalchemy.orm import Session


class GithubScanRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, values: dict[str, object]) -> GithubScanRun:
        scan_run = GithubScanRun(**values)
        self.db.add(scan_run)
        self.db.commit()
        self.db.refresh(scan_run)
        return scan_run
