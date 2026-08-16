from __future__ import annotations

import os
import hashlib
import json
from pathlib import Path

from .security import is_path_redirect


class GovernanceViolation(RuntimeError):
    """Raised when an Aegis-managed mutation targets governing input."""


def _identity(path: Path) -> tuple[int, int] | None:
    try:
        stat_result = path.stat(follow_symlinks=False)
    except OSError:
        return None
    return int(stat_result.st_dev), int(stat_result.st_ino)


def _relative_casefold(path: Path, root: Path) -> tuple[str, ...] | None:
    """Return a lexical relative identity with Windows aliases normalized."""

    try:
        relative = path.absolute().relative_to(root.absolute())
    except ValueError:
        return None
    parts = relative.parts
    if os.name == "nt":
        return tuple(part.casefold() for part in parts)
    return tuple(parts)


def _governing_file_identities(root: Path) -> set[tuple[int, int]]:
    identities: set[tuple[int, int]] = set()
    agents = root / ".agents"
    if agents.is_dir() and not is_path_redirect(agents):
        for path in agents.rglob("*"):
            identity = _identity(path)
            if identity is not None:
                identities.add(identity)
    for path in _instruction_files(root):
        identity = _identity(path)
        if identity is not None:
            identities.add(identity)
    return identities


def _instruction_files(root: Path) -> list[Path]:
    found: list[Path] = []
    excluded = {".git", ".aegis", "dist", "build", "vendor", "node_modules", "__pycache__"}
    for directory, names, files in os.walk(root, topdown=True, followlinks=False):
        names[:] = sorted(name for name in names if name not in excluded)
        base = Path(directory)
        if "AGENTS.md" in files:
            found.append(base / "AGENTS.md")
    return sorted(found, key=lambda item: item.relative_to(root).as_posix())


def _entry(path: Path, root: Path) -> dict:
    relative = path.relative_to(root).as_posix()
    if is_path_redirect(path):
        target = os.readlink(path) if path.is_symlink() else "windows-reparse-point"
        return {"path": relative, "kind": "redirect", "target": str(target)}
    if path.is_dir():
        return {"path": relative, "kind": "directory", "size": 0}
    if path.is_file():
        data = path.read_bytes()
        return {
            "path": relative,
            "kind": "file",
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    return {"path": relative, "kind": "other"}


def capture_governance(root: Path) -> dict:
    """Capture deployed governance and governing-instruction content identities."""

    project = Path(root).resolve(strict=True)
    agents = project / ".agents"
    if not agents.is_dir() or is_path_redirect(agents):
        raise GovernanceViolation("AEGIS-I001: deployed .agents root is missing or redirected")
    paths = [agents, *agents.rglob("*"), *_instruction_files(project)]
    unique = sorted(set(paths), key=lambda item: item.relative_to(project).as_posix())
    entries = [_entry(path, project) for path in unique]
    body = {
        "schema": 1,
        "project_root": str(project),
        "integrity_mode": "INTEGRITY_DETECTION",
        "preventive_scope": "AEGIS_MANAGED_MUTATION_PATHS",
        "entries": entries,
    }
    body["digest"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return body


def verify_governance(root: Path, snapshot: dict) -> dict:
    if not isinstance(snapshot, dict) or snapshot.get("schema") != 1:
        raise GovernanceViolation("AEGIS-I001: governance snapshot schema is invalid")
    project = Path(root).resolve(strict=True)
    if snapshot.get("project_root") != str(project):
        raise GovernanceViolation("AEGIS-I001: governance snapshot belongs to another project root")
    current = capture_governance(project)
    if current.get("digest") != snapshot.get("digest") or current.get("entries") != snapshot.get("entries"):
        raise GovernanceViolation(
            f"AEGIS-I001: governance integrity changed (expected {snapshot.get('digest')}, observed {current.get('digest')})"
        )
    return {"ok": True, "digest": current["digest"], "entry_count": len(current["entries"])}


def assert_mutation_allowed(root: Path, *targets: Path, operation: str = "write") -> None:
    """Deny ordinary Aegis mutations of deployed governance.

    This guard covers Aegis-managed writes, deletes, and rename endpoints.  It
    is deliberately unconditional: there is no flag or environment escape
    hatch.  Out-of-band same-user writes require independent digest detection.
    """

    project = Path(root).resolve(strict=True)
    governing_identities = _governing_file_identities(project)
    for supplied in targets:
        raw = Path(supplied)
        if not raw.is_absolute() and ".." in raw.parts:
            raise GovernanceViolation(f"AEGIS-I001: {operation} path uses parent traversal: {supplied}")
        candidate = raw if raw.is_absolute() else project / raw
        relative_parts = _relative_casefold(candidate, project)
        if relative_parts is None:
            raise GovernanceViolation(f"AEGIS-I010: {operation} target escapes project root: {supplied}")
        if relative_parts and relative_parts[0] == ".agents":
            raise GovernanceViolation(f"AEGIS-I001: deployed .agents governance is immutable: {supplied}")
        if relative_parts and relative_parts[-1] == ("agents.md" if os.name == "nt" else "AGENTS.md"):
            raise GovernanceViolation(f"AEGIS-I001: governing instruction file is immutable: {supplied}")

        current = project
        for part in candidate.absolute().relative_to(project.absolute()).parts:
            current = current / part
            if is_path_redirect(current):
                raise GovernanceViolation(f"AEGIS-I001: redirected mutation path is forbidden: {current}")

        resolved = candidate.parent.resolve(strict=False) / candidate.name
        try:
            resolved_relative = resolved.relative_to(project)
        except ValueError as exc:
            raise GovernanceViolation(f"AEGIS-I001: resolved mutation path escapes project root: {supplied}") from exc
        normalized_resolved = tuple(
            part.casefold() if os.name == "nt" else part for part in resolved_relative.parts
        )
        if normalized_resolved and normalized_resolved[0] == ".agents":
            raise GovernanceViolation(f"AEGIS-I001: resolved target enters deployed governance: {supplied}")
        identity = _identity(candidate)
        if identity is not None and identity in governing_identities:
            raise GovernanceViolation(f"AEGIS-I001: hardlinked governing content is immutable: {supplied}")
