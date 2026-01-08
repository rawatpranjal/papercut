"""Reference following - download cited papers."""

import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from papercutter.core.references import Reference, ReferenceExtractor
from papercutter.core.resolver import ReferenceResolver, ResolvedReference
from papercutter.extractors.pdfplumber import PdfPlumberExtractor
from papercutter.fetchers.base import Document
from papercutter.fetchers.registry import FetcherRegistry, get_registry


@dataclass
class FollowResult:
    """Result of following references."""

    downloaded: list[Document] = field(default_factory=list)
    failed: list[tuple[ResolvedReference, str]] = field(default_factory=list)
    unresolved: list[Reference] = field(default_factory=list)
    total_references: int = 0


@dataclass
class FollowProgress:
    """Progress state for callbacks."""

    total: int
    resolved: int
    downloaded: int
    failed: int
    current: str | None = None


class ReferenceFollower:
    """Follow and download referenced papers."""

    def __init__(
        self,
        registry: FetcherRegistry | None = None,
        max_parallel: int = 3,
        continue_on_error: bool = True,
        rate_limit_delay: float = 1.0,
    ):
        """Initialize follower.

        Args:
            registry: FetcherRegistry for downloading. Uses default if None.
            max_parallel: Maximum concurrent downloads.
            continue_on_error: Continue downloading after failures.
            rate_limit_delay: Delay between downloads in seconds.
        """
        self.registry = registry or get_registry()
        self.resolver = ReferenceResolver(self.registry)
        self.max_parallel = max_parallel
        self.continue_on_error = continue_on_error
        self.rate_limit_delay = rate_limit_delay

    def follow(
        self,
        pdf_path: Path,
        output_dir: Path,
        dry_run: bool = False,
        progress_callback: Callable[[FollowProgress], None] | None = None,
    ) -> FollowResult:
        """Follow references from a PDF.

        Args:
            pdf_path: Path to source PDF.
            output_dir: Directory to save downloaded papers.
            dry_run: If True, only resolve but don't download.
            progress_callback: Optional callback for progress updates.

        Returns:
            FollowResult with downloaded, failed, and unresolved refs.
        """
        result = FollowResult()

        # Extract references from source PDF
        extractor = ReferenceExtractor(PdfPlumberExtractor())
        references = extractor.extract(pdf_path)
        result.total_references = len(references)

        if not references:
            return result

        # Resolve references
        resolved_refs = self.resolver.resolve_all(references, deduplicate=True)

        # Separate resolved from unresolved
        to_download = [r for r in resolved_refs if r.is_resolved]
        result.unresolved = [r.reference for r in resolved_refs if not r.is_resolved]

        if progress_callback:
            progress_callback(
                FollowProgress(
                    total=len(references),
                    resolved=len(to_download),
                    downloaded=0,
                    failed=0,
                )
            )

        if dry_run or not to_download:
            return result

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Download resolved references
        if self.max_parallel > 1:
            result = self._download_parallel(
                to_download, output_dir, result, progress_callback
            )
        else:
            result = self._download_sequential(
                to_download, output_dir, result, progress_callback
            )

        return result

    def _download_sequential(
        self,
        resolved_refs: list[ResolvedReference],
        output_dir: Path,
        result: FollowResult,
        progress_callback: Callable[[FollowProgress], None] | None = None,
    ) -> FollowResult:
        """Download references sequentially."""
        for i, ref in enumerate(resolved_refs):
            if progress_callback:
                progress_callback(
                    FollowProgress(
                        total=result.total_references,
                        resolved=len(resolved_refs),
                        downloaded=len(result.downloaded),
                        failed=len(result.failed),
                        current=ref.resolved_id,
                    )
                )

            try:
                # Use registry to fetch (it will find the right fetcher)
                doc = self.registry.fetch(ref.resolved_id, output_dir)
                result.downloaded.append(doc)
            except Exception as e:
                result.failed.append((ref, str(e)))
                if not self.continue_on_error:
                    break

            # Rate limiting
            if i < len(resolved_refs) - 1:
                time.sleep(self.rate_limit_delay)

        return result

    def _download_parallel(
        self,
        resolved_refs: list[ResolvedReference],
        output_dir: Path,
        result: FollowResult,
        progress_callback: Callable[[FollowProgress], None] | None = None,
    ) -> FollowResult:
        """Download references in parallel with rate limiting."""
        with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            futures = {}
            for ref in resolved_refs:
                future = executor.submit(
                    self._download_one, ref, output_dir
                )
                futures[future] = ref

            for future in as_completed(futures):
                ref = futures[future]
                try:
                    doc = future.result()
                    result.downloaded.append(doc)
                except Exception as e:
                    result.failed.append((ref, str(e)))
                    if not self.continue_on_error:
                        # Cancel remaining futures
                        for f in futures:
                            f.cancel()
                        break

                if progress_callback:
                    progress_callback(
                        FollowProgress(
                            total=result.total_references,
                            resolved=len(resolved_refs),
                            downloaded=len(result.downloaded),
                            failed=len(result.failed),
                            current=None,
                        )
                    )

        return result

    def _download_one(
        self, ref: ResolvedReference, output_dir: Path
    ) -> Document:
        """Download a single reference."""
        # Add rate limit delay
        time.sleep(self.rate_limit_delay)
        return self.registry.fetch(ref.resolved_id, output_dir)

    def generate_manifest(
        self,
        source_pdf: Path,
        result: FollowResult,
        resolved_refs: list[ResolvedReference],
    ) -> dict[str, Any]:
        """Generate manifest.json with full resolution details.

        Args:
            source_pdf: Source PDF path.
            result: FollowResult from download.
            resolved_refs: All resolved references.

        Returns:
            Manifest dictionary.
        """
        # Build reference details
        ref_details = []
        downloaded_ids = {d.path.name for d in result.downloaded}
        failed_ids = {r[0].resolved_id for r in result.failed}

        for ref in resolved_refs:
            entry = {
                "raw_text": ref.reference.raw_text[:200],  # Truncate
            }
            if ref.is_resolved:
                entry["resolved_id"] = ref.resolved_id
                entry["source_type"] = ref.source_type
                if ref.resolved_id in failed_ids:
                    entry["status"] = "failed"
                    # Find error message
                    for failed_ref, error in result.failed:
                        if failed_ref.resolved_id == ref.resolved_id:
                            entry["error"] = error[:100]
                            break
                else:
                    entry["status"] = "downloaded"
                    # Find local path
                    for doc in result.downloaded:
                        entry["local_path"] = doc.path.name
            else:
                entry["status"] = "unresolved"

            ref_details.append(entry)

        # Group by source type
        by_source: dict[str, list[str]] = {}
        for ref in resolved_refs:
            if ref.is_resolved:
                source = ref.source_type or "unknown"
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(ref.resolved_id)

        return {
            "source_pdf": str(source_pdf.name),
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_references": result.total_references,
                "resolved": len([r for r in resolved_refs if r.is_resolved]),
                "downloaded": len(result.downloaded),
                "failed": len(result.failed),
                "unresolved": len(result.unresolved),
            },
            "by_source": by_source,
            "references": ref_details,
        }

    def write_manifest(
        self,
        output_dir: Path,
        manifest: dict[str, Any],
    ) -> Path:
        """Write manifest to file.

        Args:
            output_dir: Output directory.
            manifest: Manifest dictionary.

        Returns:
            Path to manifest file.
        """
        manifest_path = output_dir / "_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        return manifest_path

    def write_unresolved(
        self,
        output_dir: Path,
        source_pdf: Path,
        unresolved: list[Reference],
    ) -> Path:
        """Write unresolved references to file.

        Args:
            output_dir: Output directory.
            source_pdf: Source PDF path.
            unresolved: List of unresolved references.

        Returns:
            Path to unresolved file.
        """
        unresolved_path = output_dir / "_unresolved.txt"
        lines = [
            "# References that could not be resolved to downloadable sources",
            f"# Source: {source_pdf.name}",
            f"# Generated: {datetime.now().isoformat()}",
            "",
        ]
        for i, ref in enumerate(unresolved, 1):
            lines.append(f"[{i}] {ref.raw_text}")
        lines.append("")

        unresolved_path.write_text("\n".join(lines))
        return unresolved_path
