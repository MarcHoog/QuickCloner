import httpx

from typing import Dict, List
from .models import Repo

API_VERSION_PROJECTS = "7.1-preview.4"
API_VERSION_REPOS = "7.1-preview.1"



class AzDoClient:

    def __init__(self, org: str, pat: str, base_url: str = "https://dev.azure.com"):
        self.org = org
        self.pat = pat
        self.base_url = base_url.rstrip("/")
        self._client = None


    async def __aenter__(self):
            self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Accept": "application/json"},
            auth=("", self.pat),
            )
            return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()


    async def list_projects(self) -> List[Dict]:
        assert self._client
        url = f"{self.base_url}/{self.org}/_apis/projects?api-version={API_VERSION_PROJECTS}"
        projects: List[Dict] = []
        while True:
            r = await self._client.get(url)
            r.raise_for_status()
            data = r.json()
            projects.extend(data.get("value", []))
            cont = r.headers.get("x-ms-continuationtoken")
            if not cont:
                break
            url = f"{self.base_url}/{self.org}/_apis/projects?api-version={API_VERSION_PROJECTS}&$top=1000&continuationToken={cont}"

        return projects

    async def list_repos_for_project(self, project: str) -> List[Repo]:
        """Return repos for a given project (name or id)."""
        assert self._client
        url = f"{self.base_url}/{self.org}/{project}/_apis/git/repositories?api-version={API_VERSION_REPOS}&$top=1000"
        repos: List[Repo] = []
        while True:
            r = await self._client.get(url)
            if r.status_code in (401, 403):
                return []
            r.raise_for_status()
            data = r.json()
            for item in data.get("value", []):
                repos.append(
                    Repo(
                        project_name=item.get("project", {}).get("name", str(project)),
                        repo_name=item.get("name", ""),
                        remote_url=item.get("remoteUrl", ""),
                        default_branch=item.get("defaultBranch"),
                        )
                    )
            cont = r.headers.get("x-ms-continuationtoken")
            if not cont:
                break
            url = f"{self.base_url}/{self.org}/{project}/_apis/git/repositories?api-version={API_VERSION_REPOS}&$top=1000&continuationToken={cont}"
        return repos
