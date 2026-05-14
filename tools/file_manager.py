import logging
import os
import shutil
import time
from pathlib import Path

import config

logger = logging.getLogger("nexus.tools.file_manager")

_BLOCKED_ROOTS = {
    Path("C:/Windows"),
    Path("C:/Windows/System32"),
    Path("C:/Program Files"),
    Path("C:/Program Files (x86)"),
    Path("C:/ProgramData"),
}


def _safe_path(raw: str) -> Path:
    p = Path(raw).resolve()
    for blocked in _BLOCKED_ROOTS:
        try:
            p.relative_to(blocked.resolve())
            raise ValueError(f"Access to {blocked} is restricted.")
        except ValueError as exc:
            if "restricted" in str(exc):
                raise
    return p


def file_create(path: str, content: str = "") -> str:
    """Create a new file with optional content.

    Args:
        path: Full path to the file to create.
        content: Text content to write to the file (optional).
    """
    try:
        target = _safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        logger.info("Created file: %s", target)
        return f"Created file: {target.name}."
    except ValueError as exc:
        return f"Path error: {exc}"
    except Exception as exc:
        return f"Failed to create file: {exc}"


def file_delete(path: str) -> str:
    """Delete a file or empty directory.

    Args:
        path: Full path to the file or directory to delete.
    """
    try:
        target = _safe_path(path)
        if not target.exists():
            return f"Path not found: {path}"
        if target.is_dir():
            os.rmdir(str(target))
        else:
            target.unlink()
        logger.info("Deleted: %s", target)
        return f"Deleted: {target.name}."
    except ValueError as exc:
        return f"Path error: {exc}"
    except OSError as exc:
        return f"Failed to delete (may not be empty): {exc}"
    except Exception as exc:
        return f"Failed to delete: {exc}"


def file_delete_force(path: str) -> str:
    """Force-delete a file or directory (including non-empty directories).

    Args:
        path: Full path to the file or directory to delete.
    """
    try:
        target = _safe_path(path)
        if not target.exists():
            return f"Path not found: {path}"
        if target.is_dir():
            shutil.rmtree(str(target))
        else:
            target.unlink()
        logger.info("Force-deleted: %s", target)
        return f"Force-deleted: {target.name}."
    except ValueError as exc:
        return f"Path error: {exc}"
    except Exception as exc:
        return f"Failed to delete: {exc}"


def file_copy(source: str, destination: str) -> str:
    """Copy a file or directory to a new location.

    Args:
        source: Path to the source file or directory.
        destination: Destination path.
    """
    try:
        src = _safe_path(source)
        dst = _safe_path(destination)
        if not src.exists():
            return f"Source not found: {source}"
        if src.is_dir():
            shutil.copytree(str(src), str(dst))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
        logger.info("Copied %s → %s", src, dst)
        return f"Copied '{src.name}' to '{dst}'."
    except ValueError as exc:
        return f"Path error: {exc}"
    except Exception as exc:
        return f"Failed to copy: {exc}"


def file_move(source: str, destination: str) -> str:
    """Move a file or directory to a new location.

    Args:
        source: Path to the source file or directory.
        destination: Destination path.
    """
    try:
        src = _safe_path(source)
        dst = _safe_path(destination)
        if not src.exists():
            return f"Source not found: {source}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        logger.info("Moved %s → %s", src, dst)
        return f"Moved '{src.name}' to '{dst}'."
    except ValueError as exc:
        return f"Path error: {exc}"
    except Exception as exc:
        return f"Failed to move: {exc}"


def file_rename(path: str, new_name: str) -> str:
    """Rename a file or directory.

    Args:
        path: Current full path.
        new_name: New name (just the filename, not full path).
    """
    try:
        target = _safe_path(path)
        if not target.exists():
            return f"Path not found: {path}"
        new_path = target.parent / new_name
        target.rename(new_path)
        logger.info("Renamed %s → %s", target, new_path)
        return f"Renamed to '{new_name}'."
    except ValueError as exc:
        return f"Path error: {exc}"
    except Exception as exc:
        return f"Failed to rename: {exc}"


def file_read(path: str) -> str:
    """Read the contents of a text file.

    Args:
        path: Full path to the file.
    """
    try:
        target = _safe_path(path)
        if not target.exists():
            return f"File not found: {path}"
        content = target.read_text(encoding="utf-8")
        if not content:
            return f"File '{target.name}' is empty."
        if len(content) > 10000:
            content = content[:10000] + "\n\n...[truncated, file is larger]"
        return f"Contents of '{target.name}':\n{content}"
    except ValueError as exc:
        return f"Path error: {exc}"
    except UnicodeDecodeError:
        return f"File '{path}' is not a text file (binary)."
    except Exception as exc:
        return f"Failed to read file: {exc}"


def file_write(path: str, content: str) -> str:
    """Write text content to a file (overwrites existing).

    Args:
        path: Full path to the file.
        content: Text to write.
    """
    try:
        target = _safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        logger.info("Wrote to: %s", target)
        preview = content[:60] + "..." if len(content) > 60 else content
        return f"Wrote to '{target.name}': {preview}"
    except ValueError as exc:
        return f"Path error: {exc}"
    except Exception as exc:
        return f"Failed to write file: {exc}"


def file_append(path: str, content: str) -> str:
    """Append text content to a file.

    Args:
        path: Full path to the file.
        content: Text to append.
    """
    try:
        target = _safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(str(target), "a", encoding="utf-8") as f:
            f.write(content)
        logger.info("Appended to: %s", target)
        return f"Appended to '{target.name}'."
    except ValueError as exc:
        return f"Path error: {exc}"
    except Exception as exc:
        return f"Failed to append: {exc}"


def file_list(directory: str = "") -> str:
    """List the contents of a directory.

    Args:
        directory: Directory path. Defaults to user's home folder.
    """
    if not directory:
        directory = str(Path.home())
    try:
        target = _safe_path(directory)
        if not target.is_dir():
            return f"'{directory}' is not a valid directory."
        entries = list(target.iterdir())
        if not entries:
            return f"Directory '{target}' is empty."
        folders = []
        files = []
        for e in sorted(entries, key=lambda x: (not x.is_dir(), x.name.lower())):
            if e.is_dir():
                folders.append(f"  📁 {e.name}/")
            else:
                size = e.stat().st_size
                if size > 1024 * 1024:
                    size_str = f"{size / (1024*1024):.1f} MB"
                elif size > 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size} B"
                files.append(f"  📄 {e.name} ({size_str})")
        result = f"Contents of {target}:\n"
        result += "\n".join(folders + files)
        if len(entries) > 100:
            result += f"\n  … and {len(entries) - 100} more."
        return result
    except ValueError as exc:
        return f"Path error: {exc}"
    except Exception as exc:
        return f"Failed to list directory: {exc}"


def file_info(path: str) -> str:
    """Get metadata about a file or directory.

    Args:
        path: Full path to the file or directory.
    """
    try:
        target = _safe_path(path)
        if not target.exists():
            return f"Path not found: {path}"
        stat = target.stat()
        lines = [
            f"Name: {target.name}",
            f"Path: {target}",
            f"Type: {'Directory' if target.is_dir() else 'File'}",
            f"Size: {stat.st_size:,} bytes",
            f"Created: {time.ctime(stat.st_ctime)}",
            f"Modified: {time.ctime(stat.st_mtime)}",
            f"Accessed: {time.ctime(stat.st_atime)}",
        ]
        return "\n".join(lines)
    except ValueError as exc:
        return f"Path error: {exc}"
    except Exception as exc:
        return f"Failed to get file info: {exc}"


def file_download(url: str, destination: str = "") -> str:
    """Download a file from a URL to a local path.

    Args:
        url: The URL to download from.
        destination: Full path where to save the file. Defaults to Downloads folder.
    """
    try:
        import urllib.request
    except ImportError:
        return "urllib not available."

    if not destination:
        destination = str(Path.home() / "Downloads")

    try:
        dst = Path(destination)
        if dst.is_dir():
            filename = url.split("/")[-1].split("?")[0] or "download"
            dst = dst / filename
        dst = _safe_path(str(dst))
        dst.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Downloading %s → %s", url, dst)
        urllib.request.urlretrieve(url, str(dst))
        return f"Downloaded to {dst}."
    except ValueError as exc:
        return f"Path error: {exc}"
    except Exception as exc:
        return f"Download failed: {exc}"
