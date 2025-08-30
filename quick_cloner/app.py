### `azdo_clone_tui/app.py`
"""
app.py — Textual TUI for selecting and cloning Azure DevOps repositories

This module defines the `AzDoCloneApp` class, which provides a terminal-based
UI to:
  - Load projects and repos from Azure DevOps (via AzDoClient).
  - Display them in a filterable DataTable.
  - Allow the user to select repos.
  - Clone/pull the selected repos concurrently (via CloneWorker).

Key controls:
  q : Quit the app
  r : Refresh data from Azure DevOps
  / : Focus the filter input field
  a : Select all visible repos
  n : Clear all selections
  c : Clone selected repos
"""

import anyio
import sys
import httpx
from pathlib import Path
from typing import List, Tuple, Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Log,
)

from .azdo import AzDoClient
from .clone import CloneWorker
from .utils import mask_pat
from .models import Repo
from .log import _LogStream
from textual.events import Key


class AzDoCloneApp(App):
    """Main Textual app for browsing and cloning repos."""

    CSS = """
    Screen { layout: vertical; }
    #toolbar { height: 3; }
    #controls { height: 3; }
    #table { height: 1fr; }
    #log { height: 10; }
    Button { margin: 0 1; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("a", "select_all", "Select ALL"),
        Binding("/", "focus_filter", "Filter"),
        Binding("c", "clone_selected", "Clone"),
    ]

    class ReposLoaded(Message):
        """Custom message fired when repos have been loaded from Azure DevOps."""
        def __init__(self, repos: List[Repo]) -> None:
            self.repos = repos
            super().__init__()

    def __init__(self, org: str, pat: str, dest: Path, base_url: str, concurrency: int, pat_username: str):
        super().__init__()
        self.org = org
        self.pat = pat
        self.dest = dest
        self.base_url = base_url
        self.concurrency = concurrency
        self.pat_username = pat_username

        # Internal state
        self.all_repos: List[Repo] = []
        self.filtered_repos: List[Repo] = []
        self.selected_rows: dict[int, Any] = {}

    def compose(self) -> ComposeResult:
        """Builds the widget tree for the app."""
        yield Header(show_clock=False)
        with Horizontal(id="toolbar"):
            yield Label(f"Org: {self.org}")
            yield Label("Dest:")
            self.dest_input = Input(value=str(self.dest), placeholder="Destination folder", id="dest")
            yield self.dest_input
            yield Button("Refresh", id="refresh")
            yield Button("Clone Selected", id="clone")
        with Horizontal(id="controls"):
            yield Label("Filter:")
            self.filter_input = Input(placeholder="Type to filter project/repo… (press / to focus)", id="filter")
            yield self.filter_input
        self.table = DataTable(id="table", zebra_stripes=True, cursor_type="row")
        # Ensure row-based cursor/activation so Enter/Click selects rows
        try:
            self.table.cursor_type = "row"
        except Exception:
            pass
        self.column_keys = self.table.add_columns("✔", "Project", "Repository", "Default Branch")
        yield self.table
        self.log_widget = Log(id="log")
        yield self.log_widget
        yield Footer()

    async def on_mount(self) -> None:
        """Called when the app starts up."""
        # Redirect stdout/stderr to the Log widget so plain prints show up there
        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr
        sys.stdout = _LogStream(self, mask_fn=mask_pat, secret=self.pat, tee=self._orig_stdout)
        sys.stderr = _LogStream(self, mask_fn=mask_pat, secret=self.pat, tee=self._orig_stderr)
        await self.load_data()
        self.filter_input.focus()

    async def on_unmount(self) -> None:
        """Restore original stdio when the app exits."""
        try:
            if hasattr(self, "_orig_stdout") and self._orig_stdout is not None:
                sys.stdout = self._orig_stdout  # type: ignore[assignment]
            if hasattr(self, "_orig_stderr") and self._orig_stderr is not None:
                sys.stderr = self._orig_stderr  # type: ignore[assignment]
        except Exception:
            pass

    async def load_data(self) -> None:
        """Fetch projects and repos from Azure DevOps and populate the table."""
        print(f"Fetching projects/repos from {self.base_url} for org '{self.org}'…")
        try:
            async with AzDoClient(self.org, self.pat, self.base_url) as client:
                projects = await client.list_projects()
                print(f"Found {len(projects)} projects. Fetching repos…")
                repos: List[Repo] = []

                async def fetch_project(project_name: str):
                    rs = await client.list_repos_for_project(project_name)
                    if not rs:
                        print(f"No access or no repos in project: {project_name}")
                    return rs

                async with anyio.create_task_group() as tg:
                    results: List[List[Repo]] = []

                    async def add_for(pname: str):
                        rs = await fetch_project(pname)
                        results.append(rs)

                    for p in projects:
                        pname = p.get("name")
                        if pname:
                            tg.start_soon(add_for, pname)

                for group in results:
                    repos.extend(group)

            self.all_repos = sorted(repos, key=lambda r: (r.project_name.lower(), r.repo_name.lower()))
            await self.refresh_table()
            print(f"Loaded {len(self.all_repos)} repositories.")
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e.response.status_code} {e.response.text}")
        except Exception as e:
            print(f"Error: {e}")

    async def refresh_table(self) -> None:
        """Refresh the repo DataTable based on current filter."""
        filt = self.filter_input.value.strip().lower()
        if filt:
            self.filtered_repos = [r for r in self.all_repos if filt in r.match_text()]
        else:
            self.filtered_repos = list(self.all_repos)

        self.table.clear()
        self.selected_rows.clear()

        for idx, r in enumerate(self.filtered_repos):
            self.table.add_row(" ", r.project_name, r.repo_name, r.default_branch or "", key=idx)


    async def select_row(self, row_index, row_key):
        if row_index in self.selected_rows:
            self.selected_rows.pop(row_index)
            self.table.update_cell(row_key, self.column_keys[0], " " )
        else:
            self.selected_rows[row_index] = row_key
            self.table.update_cell(row_key, self.column_keys[0], "✔" )

    async def action_refresh(self) -> None:
        await self.load_data()

    async def action_focus_filter(self) -> None:
        self.filter_input.focus()

    async def action_select_all(self) -> None:
        for row_index, row_key in enumerate(self.table.rows):
            await self.select_row(row_index, row_key)

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input is self.filter_input:
            await self.refresh_table()

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Toggle selection when a row is activated (Enter/Space or click)."""
        try:
            row_key = getattr(event, "row_key", None)
            if row_key is None:
                print(f"Nothing to happen {event}")
                return

            row_index = self.table.get_row_index(row_key)

            print(f" Row index: {row_index}")
            await self.select_row(row_index, row_key)


        except Exception as e:
            print(f"Selection error: {e}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh":
            await self.load_data()
        elif event.button.id == "clone":
            await self.action_clone_selected()
        elif event.button.id == "select_all":
            await self.action_select_all()

    def on_key(self, event: Key) -> None:
        if self.filter_input.has_focus and event.key == "enter":
            self.table.focus()

    async def action_clone_selected(self) -> None:
        if not self.selected_rows:
            print("Nothing selected.")
            return
        dest_path = Path(self.dest_input.value).expanduser().resolve()
        dest_path.mkdir(parents=True, exist_ok=True)

        to_clone = [self.filtered_repos[i] for i in sorted(self.selected_rows)]
        print(f"Cloning {len(to_clone)} repos into {dest_path} with concurrency={self.concurrency}…")

        worker = CloneWorker(
            dest_path,
            concurrency=self.concurrency,
            pat_username=self.pat_username,
            pat=self.pat,
        )

        successes = 0
        failures = 0

        async def log_cb(line: str):
            masked = mask_pat(line, self.pat)
            print(masked)

        async with anyio.create_task_group() as tg:
            results: List[Tuple[Repo, int]] = []

            async def run_clone(r: Repo):
                res = await worker.clone_one(r, log_cb)
                results.append(res)

            for r in to_clone:
                tg.start_soon(run_clone, r)

        for _, rc in results:
            if rc == 0:
                successes += 1
            else:
                failures += 1

        print(f"Done. Success: {successes}, Failures: {failures}.")

    def _log_line(self, line: str) -> None:
        try:
            log_widget = getattr(self, "log_widget", None)
            if log_widget is None:
                return
            if hasattr(log_widget, "write_line"):
                log_widget.write_line(line)
            elif hasattr(log_widget, "write"):
                log_widget.write(line + "\n")
        except Exception:
            # Don't let logging failures crash the UI
            pass
