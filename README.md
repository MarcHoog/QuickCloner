QuickCloner/README.md
# QuickCloner

![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Textual UI](https://img.shields.io/badge/UI-Textual-informational.svg)
![Azure DevOps](https://img.shields.io/badge/Azure%20DevOps-Repo%20Cloner-purple.svg)

A terminal-based TUI for selecting and cloning multiple Azure DevOps repositories at once.

## Features

- Browse Azure DevOps projects and repositories in a filterable table.
- Select multiple repositories to clone or pull concurrently.
- Fast, keyboard-driven interface.
- Skips repositories that are already cloned.

## Installation

1. Clone this repository:
    ```
    git clone https://github.com/yourusername/QuickCloner.git
    cd QuickCloner
    ```

2. Create a virtual environment (recommended):
    ```
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3. Install dependencies:
    ```
    pip install -r requirements.txt
    ```

## Usage

1. Set your Azure DevOps Personal Access Token (PAT) in your environment:
    ```
    export AZDO_PAT=your_pat_here
    ```

2. Run the TUI:
    ```
    python -m quick_cloner --org your-org-name --dest /path/to/clone
    ```

   Optional arguments:
   - `--base-url`: Custom Azure DevOps URL (default: https://dev.azure.com)
   - `--concurrency`: Max concurrent clones (default: 4)
   - `--pat-username`: Username for embedding PAT (default: azdo)

## License

See [LICENSE](LICENSE) for details.
# QuickCloner
