import asyncio
import os
import shlex
from pathlib import Path
from typing import Callable, Awaitable

from .models import Repo
from .utils import embed_pat_in_url, mask_pat


class CloneWorker:
    """Clones repos with embedded PAT. Skips repos that already exist."""

    def __init__(self, dest: Path, concurrency: int = 4, *, pat_username: str = "azdo", pat: str = ""):
        self.dest = dest
        self.sem = asyncio.Semaphore(concurrency)
        self.pat_username = pat_username
        self.pat = pat

    async def clone_one(self, repo: Repo, log_cb: Callable[[str], Awaitable[None]]):
        target = self.dest / repo.repo_name

        # Skip if already cloned
        if (target / ".git").exists():
            await log_cb(f"→ SKIP {repo.project_name}/{repo.repo_name}: already exists")
            return repo, 0

        remote_url = embed_pat_in_url(repo.remote_url, self.pat_username, self.pat)
        cmd = ["git", "clone", "--origin", "origin", remote_url, str(target)]

        env = os.environ.copy()
        env.setdefault("GIT_TERMINAL_PROMPT", "0")

        masked_cmd = mask_pat(" ".join(shlex.quote(c) for c in cmd), self.pat)
        await log_cb(f"→ CLONE {repo.project_name}/{repo.repo_name}: {masked_cmd}")

        async with self.sem:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
            stdout, _ = await proc.communicate()
            out = stdout.decode(errors="replace")
            rc = proc.returncode
            for line in out.splitlines():
                await log_cb(f" {mask_pat(line, self.pat)}")

            status = "OK" if rc == 0 else f"FAIL({rc})"
            await log_cb(f"← CLONE {repo.project_name}/{repo.repo_name}: {status}\n")
            return repo, rc
