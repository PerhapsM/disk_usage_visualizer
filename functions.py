import os
from typing import Dict, Tuple, List


def get_windows_drives() -> List[str]:
    """Return a list of existing Windows drive letters (e.g. 'C:', 'D:').

    Returns:
        List[str]: list of drive strings (including colon), empty on non-Windows.
    """
    drives = []
    for drive in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if os.path.exists(f"{drive}:"):
            drives.append(f"{drive}:")

    return drives


def get_folder_size(path: str) -> int:
    """Return total size in bytes for all files under *path*.

    Args:
        path: Path to the directory to scan.

    Returns:
        int: Total size in bytes. Skips files/dirs that raise permission errors.
    """
    total_size = 0

    try:
        for dirpath, _dirnames, filenames in os.walk(path):
            for filename in filenames:
                try:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
                except (OSError, FileNotFoundError):
                    pass
    except (PermissionError, OSError):
        pass

    return total_size


def format_size(bytes_size: int) -> str:
    """Convert bytes to a human readable string.

    Args:
        bytes_size: Size in bytes.

    Returns:
        str: Formatted size, e.g. '1.23 GB'.
    """
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024

    return f"{bytes_size:.2f} PB"


def get_folder_breakdown(path: str, max_depth: int = 3, current_depth: int = 0) -> Dict:
    """Return a mapping of direct subfolders to their sizes and nested subdirs.

    Args:
        path: Root path to analyze.
        max_depth: Maximum recursion depth (1 = top-level folders only).
        current_depth: Internal recursion depth counter (used by callers).

    Returns:
        dict: Mapping {folder_name: {'size': int, 'path': str, 'subdirs': dict}}
    """
    if current_depth >= max_depth:
        return {}

    breakdown = {}
    try:
        items = os.listdir(path)
    except (PermissionError, OSError):
        return breakdown

    for item in items:
        try:
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                size = get_folder_size(item_path)
                breakdown[item] = {
                    "size": size,
                    "path": item_path,
                    "subdirs": get_folder_breakdown(
                        item_path, max_depth, current_depth + 1
                    ),
                }
        except (PermissionError, OSError):
            pass

    return breakdown


def build_sunburst_data(
    breakdown: Dict, root_id: str
) -> Tuple[List[str], List[str], List[int], List[str], List[str]]:
    """Build sunburst arrays from a folder breakdown structure.

    Args:
        breakdown: Result from `get_folder_breakdown` for a root path.
        root_id: Unique id to use for the root node (prefer full path).

    Returns:
        labels, parents, values, ids, formatted_sizes
    """
    labels = []
    parents = []
    values = []
    ids = []
    formatted = []

    # Root node
    total_size = sum(item[1]["size"] for item in breakdown.items()) if breakdown else 0
    labels.append("Root")
    parents.append("")
    values.append(total_size)
    ids.append(root_id)
    formatted.append(format_size(total_size))

    def add_folder(folder_name: str, folder_data: Dict, parent_id: str) -> None:
        node_id = folder_data.get("path") or f"{parent_id}/{folder_name}"
        labels.append(folder_name)
        parents.append(parent_id)
        values.append(folder_data["size"])
        ids.append(node_id)
        formatted.append(format_size(folder_data["size"]))

        if folder_data.get("subdirs"):
            for sub_name, sub_data in folder_data["subdirs"].items():
                add_folder(sub_name, sub_data, node_id)

    for name, data in breakdown.items():
        add_folder(name, data, root_id)

    return labels, parents, values, ids, formatted
