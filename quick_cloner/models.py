from dataclasses import dataclass
from typing import Optional

@dataclass
class Repo:
    project_name: str
    repo_name: str
    remote_url: str
    default_branch: Optional[str] = None

    def match_text(self) -> str:
        return f"{self.project_name}/{self.repo_name}".lower()
