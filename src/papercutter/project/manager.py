"""Project manager for Papercutter Factory.

Handles the .papercutter/ project folder creation, loading, and saving.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from papercutter.project.inventory import ProjectInventory
from papercutter.project.state import ProjectConfig


class ProjectError(Exception):
    """Error related to project operations."""

    pass


class ProjectNotFoundError(ProjectError):
    """Project folder not found."""

    pass


class ProjectExistsError(ProjectError):
    """Project already exists."""

    pass


class ProjectManager:
    """Manages .papercutter/ project folder.

    The project folder structure:
        .papercutter/
        ├── config.yaml         # Project configuration
        ├── inventory.json      # Paper tracking
        ├── raw_md/             # Docling output (Markdown)
        ├── tables/             # Extracted tables (JSON)
        ├── extractions/        # LLM extraction results
        └── generated.bib       # Auto-generated BibTeX for orphan PDFs
    """

    PROJECT_DIR = ".papercutter"
    CONFIG_FILE = "config.yaml"
    INVENTORY_FILE = "inventory.json"
    RAW_MD_DIR = "raw_md"
    TABLES_DIR = "tables"
    EXTRACTIONS_DIR = "extractions"
    GENERATED_BIB = "generated.bib"

    def __init__(self, root: Path):
        """Initialize the project manager.

        Args:
            root: Root directory of the project (contains .papercutter/).
        """
        self.root = Path(root).resolve()
        self.project_dir = self.root / self.PROJECT_DIR

        # Loaded state (set by load() or init_project())
        self._config: ProjectConfig | None = None
        self._inventory: ProjectInventory | None = None

    @property
    def config(self) -> ProjectConfig:
        """Get loaded project config. Call load() first."""
        if self._config is None:
            raise ProjectNotFoundError("Project not loaded. Call load() first.")
        return self._config

    @property
    def inventory(self) -> ProjectInventory:
        """Get loaded project inventory. Call load() first."""
        if self._inventory is None:
            raise ProjectNotFoundError("Project not loaded. Call load() first.")
        return self._inventory

    @property
    def config_path(self) -> Path:
        """Path to config.yaml."""
        return self.project_dir / self.CONFIG_FILE

    @property
    def inventory_path(self) -> Path:
        """Path to inventory.json."""
        return self.project_dir / self.INVENTORY_FILE

    @property
    def raw_md_dir(self) -> Path:
        """Path to raw_md/ directory."""
        return self.project_dir / self.RAW_MD_DIR

    @property
    def tables_dir(self) -> Path:
        """Path to tables/ directory."""
        return self.project_dir / self.TABLES_DIR

    @property
    def extractions_dir(self) -> Path:
        """Path to extractions/ directory."""
        return self.project_dir / self.EXTRACTIONS_DIR

    @property
    def generated_bib_path(self) -> Path:
        """Path to generated.bib."""
        return self.project_dir / self.GENERATED_BIB

    def exists(self) -> bool:
        """Check if project exists."""
        return self.project_dir.exists()

    def init(
        self,
        name: str | None = None,
        bibtex_path: Path | None = None,
        force: bool = False,
    ) -> tuple[ProjectConfig, ProjectInventory]:
        """Initialize a new project.

        Creates the .papercutter/ directory structure and initial config.

        Args:
            name: Project name. Defaults to parent directory name.
            bibtex_path: Path to BibTeX file to link.
            force: If True, reinitialize existing project.

        Returns:
            Tuple of (ProjectConfig, ProjectInventory).

        Raises:
            ProjectExistsError: If project exists and force=False.
        """
        if self.exists() and not force:
            raise ProjectExistsError(
                f"Project already exists at {self.project_dir}. "
                "Use force=True to reinitialize."
            )

        # Create directory structure
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.raw_md_dir.mkdir(exist_ok=True)
        self.tables_dir.mkdir(exist_ok=True)
        self.extractions_dir.mkdir(exist_ok=True)

        # Create markdown directory (used by ingestion pipeline)
        markdown_dir = self.project_dir / "markdown"
        markdown_dir.mkdir(exist_ok=True)

        # Create chunks directory (used by splitter)
        chunks_dir = self.project_dir / "chunks"
        chunks_dir.mkdir(exist_ok=True)

        # Create input directory if it doesn't exist
        input_dir = self.root / "input"
        input_dir.mkdir(exist_ok=True)

        # Create config
        config = ProjectConfig(
            name=name or self.root.name,
            bibtex_path=str(bibtex_path.relative_to(self.root)) if bibtex_path else None,
        )
        self.save_config(config)

        # Create empty inventory
        inventory = ProjectInventory()
        self.save_inventory(inventory)

        # Store as instance state
        self._config = config
        self._inventory = inventory

        return config, inventory

    def init_project(
        self,
        name: str | None = None,
        bib_path: Path | None = None,
    ) -> None:
        """Initialize a new project (simpler interface for CLI).

        Args:
            name: Project name.
            bib_path: Path to BibTeX file.
        """
        self.init(name=name, bibtex_path=bib_path, force=False)

    def load(self) -> tuple[ProjectConfig, ProjectInventory]:
        """Load existing project.

        Returns:
            Tuple of (ProjectConfig, ProjectInventory).

        Raises:
            ProjectNotFoundError: If project doesn't exist.
        """
        if not self.exists():
            raise ProjectNotFoundError(
                f"No project found at {self.root}. "
                "Run 'papercutter init' to create one."
            )

        config = self.load_config()
        inventory = self.load_inventory()

        # Store as instance state
        self._config = config
        self._inventory = inventory

        return config, inventory

    def save(self) -> None:
        """Save current config and inventory to disk."""
        if self._config is not None:
            self.save_config(self._config)
        if self._inventory is not None:
            self.save_inventory(self._inventory)

    def load_config(self) -> ProjectConfig:
        """Load project configuration.

        Returns:
            ProjectConfig instance.

        Raises:
            ProjectNotFoundError: If config file doesn't exist.
        """
        if not self.config_path.exists():
            raise ProjectNotFoundError(f"Config file not found: {self.config_path}")
        return ProjectConfig.load(self.config_path)

    def save_config(self, config: ProjectConfig) -> None:
        """Save project configuration.

        Args:
            config: ProjectConfig to save.
        """
        config.save(self.config_path)

    def load_inventory(self) -> ProjectInventory:
        """Load project inventory.

        Returns:
            ProjectInventory instance.

        Raises:
            ProjectNotFoundError: If inventory file doesn't exist.
        """
        if not self.inventory_path.exists():
            raise ProjectNotFoundError(f"Inventory not found: {self.inventory_path}")

        with open(self.inventory_path) as f:
            data = json.load(f)
        return ProjectInventory.from_dict(data)

    def save_inventory(self, inventory: ProjectInventory) -> None:
        """Save project inventory atomically.

        Uses temp file + rename to prevent corruption if interrupted.

        Args:
            inventory: ProjectInventory to save.
        """
        self._atomic_json_write(self.inventory_path, inventory.to_dict())

    def _atomic_json_write(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON data atomically using temp file + rename.

        This prevents corruption if the process is interrupted mid-write.

        Args:
            path: Target file path.
            data: JSON-serializable data.
        """
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        tmp_path.rename(path)  # Atomic on POSIX systems

    def get_relative_path(self, absolute_path: Path) -> str:
        """Convert absolute path to path relative to project root.

        Args:
            absolute_path: Absolute path to convert.

        Returns:
            Relative path string.
        """
        return str(Path(absolute_path).relative_to(self.root))

    def get_absolute_path(self, relative_path: str) -> Path:
        """Convert relative path to absolute path.

        Args:
            relative_path: Path relative to project root.

        Returns:
            Absolute Path.
        """
        return self.root / relative_path

    def get_markdown_path(self, paper_id: str) -> Path:
        """Get path for a paper's markdown file.

        Args:
            paper_id: Paper ID.

        Returns:
            Path to the markdown file.
        """
        return self.raw_md_dir / f"{paper_id}.md"

    def get_tables_path(self, paper_id: str) -> Path:
        """Get path for a paper's tables JSON file.

        Args:
            paper_id: Paper ID.

        Returns:
            Path to the tables JSON file.
        """
        return self.tables_dir / f"{paper_id}_tables.json"

    def get_extraction_path(self, paper_id: str) -> Path:
        """Get path for a paper's extraction results.

        Args:
            paper_id: Paper ID.

        Returns:
            Path to the extraction JSON file.
        """
        return self.extractions_dir / f"{paper_id}_extraction.json"

    def status_summary(self) -> dict[str, Any]:
        """Get a summary of project status.

        Returns:
            Dictionary with status information.
        """
        if not self.exists():
            return {"exists": False}

        config, inventory = self.load()

        return {
            "exists": True,
            "name": config.name,
            "root": str(self.root),
            "bibtex_path": config.bibtex_path,
            "papers": {
                "total": inventory.total_count,
                "pending": inventory.pending_count,
                "ingested": inventory.ingested_count,
                "failed": inventory.failed_count,
            },
            "schema_columns": len(config.grinding.columns),
        }


def find_project_root(start_path: Path | None = None) -> Path | None:
    """Find the project root by looking for .papercutter/ directory.

    Searches upward from start_path (or cwd) until finding .papercutter/.

    Args:
        start_path: Directory to start searching from. Defaults to cwd.

    Returns:
        Path to project root, or None if not found.
    """
    if start_path is None:
        start_path = Path.cwd()

    current = Path(start_path).resolve()

    while current != current.parent:
        if (current / ProjectManager.PROJECT_DIR).exists():
            return current
        current = current.parent

    # Check root level
    if (current / ProjectManager.PROJECT_DIR).exists():
        return current

    return None


def get_project_manager(path: Path | None = None) -> ProjectManager:
    """Get a ProjectManager for the current or specified project.

    Args:
        path: Explicit project path, or None to auto-detect.

    Returns:
        ProjectManager instance.

    Raises:
        ProjectNotFoundError: If no project found.
    """
    if path is not None:
        return ProjectManager(path)

    root = find_project_root()
    if root is None:
        raise ProjectNotFoundError(
            "No project found in current directory or parents. "
            "Run 'papercutter init' to create one."
        )

    return ProjectManager(root)
