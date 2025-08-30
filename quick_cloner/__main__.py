import argparse
import os
import sys
from pathlib import Path
from shutil import which

from .app import AzDoCloneApp

def parse_args(argv):
    p = argparse.ArgumentParser(description="Azure DevOps multi-repo cloner (Textual TUI)")
    p.add_argument("--org", default=os.environ.get("AZDO_ORG", ""), help="Azure DevOps organization name")
    p.add_argument("--dest", default=os.getcwd(), help="Destination folder for clones")
    p.add_argument("--base-url", default=os.environ.get("AZDO_BASE_URL", "https://dev.azure.com"))
    p.add_argument("--pat-env", default="AZDO_PAT", help="Environment variable containing the PAT")
    p.add_argument("--concurrency", type=int, default=4, help="Max concurrent clones")
    p.add_argument("--pat-username", default=os.environ.get("AZDO_PAT_USER", "azdo"), help="Username to use when embedding PAT")
    return p.parse_args(argv)

def main(argv):
    args = parse_args(argv)

    if not args.org:
        print("--org or AZDO_ORG is required", file=sys.stderr)
        return 2

    pat = os.environ.get(args.pat_env, "")
    if not pat:
        print(f"Missing PAT. Please set {args.pat_env}.", file=sys.stderr)
        return 2

    if which("git") is None:
        print("Git not found on PATH.", file=sys.stderr)
        return 2

    dest = Path(args.dest).expanduser()
    app = AzDoCloneApp(
        org=args.org,
        pat=pat,
        dest=dest,
        base_url=args.base_url,
        concurrency=args.concurrency,
        pat_username=args.pat_username,
    )
    app.run()
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
