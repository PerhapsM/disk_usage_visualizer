"""disk_usage_standalone
=================================

Standalone disk usage visualizer utilities and simple CLI/GUI runner.

This module provides lightweight, Streamlit-free helpers to scan a folder
tree, produce HTML/JSON reports, and optionally write an interactive
Plotly sunburst if ``plotly`` is installed.

Usage examples
--------------
- CLI: ``python disk_usage_standalone.py C:\\path\\to\\folder``
- GUI: ``python disk_usage_standalone.py --gui``

The public helpers replicate the docstring style used in
``functions.py`` (typed ``Args`` / ``Returns`` sections).
"""

import os
import sys
import json
from datetime import datetime

import tkinter as tk
from tkinter import filedialog, messagebox

# Try to import optional visualization libraries
try:
    import plotly.graph_objects as go
    import plotly.express as px

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def get_folder_size(path: str) -> int:
    """Return total size (bytes) for all files under *path*.

    Args:
        path: Filesystem path to the directory to scan.

    Returns:
        int: Total size in bytes. Files/dirs that cannot be accessed are
        skipped silently.
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
                    # skip inaccessible files
                    pass
    except (PermissionError, OSError):
        # skip directories we cannot traverse
        pass

    return total_size


def format_size(bytes_size: int) -> str:
    """Convert a byte count to a human-readable string.

    Args:
        bytes_size: Number of bytes.

    Returns:
        str: Formatted size string (e.g. ``'1.23 GB'``).
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} PB"


def get_folder_breakdown(path: str, max_depth: int = 3, current_depth: int = 0) -> dict:
    """Return a mapping of subfolders to sizes and nested subdirs.

    Args:
        path: Root directory to inspect.
        max_depth: Maximum recursion depth (1 = top-level only).
        current_depth: Internal recursion counter (used by callers).

    Returns:
        dict: Mapping ``{folder_name: {'size': int, 'path': str, 'subdirs': dict}}``.
        Empty dict is returned if the directory cannot be listed or the
        recursion limit is reached.
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


def print_tree(breakdown: dict, indent: int = 0, max_items: int = 20) -> None:
    """Print a short, human-friendly folder tree to stdout.

    Args:
        breakdown: Result returned by :func:`get_folder_breakdown`.
        indent: Initial indentation level (used for recursion).
        max_items: Maximum number of entries to show at each level.

    Returns:
        None
    """
    sorted_items = sorted(breakdown.items(), key=lambda x: x[1]["size"], reverse=True)[
        :max_items
    ]

    for name, data in sorted_items:
        print(f"{'  ' * indent}📁 {name:40} {format_size(data['size']):>12}")
        if data["subdirs"] and indent < 2:
            print_tree(data["subdirs"], indent + 1, max_items=5)


def create_html_report(
    breakdown: dict, root_path: str, output_file: str = "disk_usage_report.html"
) -> str:
    """Create a standalone HTML report and save it to disk.

    Args:
        breakdown: Folder breakdown from :func:`get_folder_breakdown`.
        root_path: The path that was analyzed (displayed in the report).
        output_file: Output filename for the HTML file.

    Returns:
        str: Path to the written HTML file.
    """

    sorted_folders = sorted(breakdown.items(), key=lambda x: x[1]["size"], reverse=True)

    total_size = sum(item[1]["size"] for item in sorted_folders)

    # Create HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Disk Usage Report</title>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
            }}
            .metrics {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }}
            .metric {{
                background: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .metric-label {{
                color: #666;
                font-size: 12px;
                text-transform: uppercase;
            }}
            .metric-value {{
                font-size: 24px;
                font-weight: bold;
                color: #333;
                margin-top: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                margin: 20px 0;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            thead {{
                background: #667eea;
                color: white;
            }}
            th {{
                padding: 12px;
                text-align: left;
            }}
            td {{
                padding: 12px;
                border-bottom: 1px solid #eee;
            }}
            tr:hover {{
                background: #f9f9f9;
            }}
            .bar {{
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                height: 20px;
                border-radius: 3px;
            }}
            .percent {{
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>💾 Disk Usage Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Path: {root_path}</p>
        </div>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-label">Total Size</div>
                <div class="metric-value">{format_size(total_size)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Folders Analyzed</div>
                <div class="metric-value">{len(sorted_folders)}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Largest Folder</div>
                <div class="metric-value">{format_size(sorted_folders[0][1]['size']) if sorted_folders else 'N/A'}</div>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Folder Name</th>
                    <th>Size</th>
                    <th>Percentage</th>
                    <th>Visual</th>
                </tr>
            </thead>
            <tbody>
    """

    for folder_name, folder_data in sorted_folders[:50]:  # Top 50
        size = folder_data["size"]
        percentage = (size / total_size * 100) if total_size > 0 else 0
        bar_width = max(percentage, 2)  # Minimum 2% for visibility

        html_content += f"""
                <tr>
                    <td>{folder_name[:50]}</td>
                    <td>{format_size(size)}</td>
                    <td>{percentage:.1f}%</td>
                    <td>
                        <div class="bar" style="width: {bar_width}%; display: inline-block;"></div>
                    </td>
                </tr>
        """

    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ HTML report saved to: {output_file}")
    return output_file


def create_json_report(
    breakdown: dict, root_path: str, output_file: str = "disk_usage_report.json"
) -> str:
    """Create a JSON report and save it to disk.

    Args:
        breakdown: Folder breakdown from :func:`get_folder_breakdown`.
        root_path: The path that was analyzed (displayed in the report).
        output_file: Output filename for the JSON file.

    Returns:
        str: Path to the written JSON file.
    """

    sorted_folders = sorted(breakdown.items(), key=lambda x: x[1]["size"], reverse=True)

    total_size = sum(item[1]["size"] for item in sorted_folders)

    report = {
        "generated": datetime.now().isoformat(),
        "root_path": root_path,
        "total_size": total_size,
        "total_size_formatted": format_size(total_size),
        "folders_analyzed": len(sorted_folders),
        "folders": [
            {
                "name": name,
                "size": data["size"],
                "size_formatted": format_size(data["size"]),
                "percentage": round(
                    (data["size"] / total_size * 100) if total_size > 0 else 0, 2
                ),
                "path": data["path"],
            }
            for name, data in sorted_folders
        ],
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"✅ JSON report saved to: {output_file}")
    return output_file


def main_cli(path: str = None, max_depth: int = 2) -> None:
    """Run the utility in CLI mode.

    If *path* is not provided the user is prompted; pressing Enter uses the
    current working directory.

    Args:
        path: Optional path to analyze. If omitted the user is prompted.
        max_depth: Maximum recursion depth for the scan.

    Returns:
        None
    """
    if not path:
        path = input(
            "Enter folder path (or press Enter for current directory): "
        ).strip()
        if not path:
            path = os.getcwd()

    if not os.path.isdir(path):
        print(f"❌ Invalid path: {path}")
        return

    print(f"📁 Analyzing: {path}")
    print("⏳ Please wait...\n")

    breakdown = get_folder_breakdown(path, max_depth)

    if not breakdown:
        print("No subfolders found or access denied.")
        return

    total_size = sum(item["size"] for item in breakdown.values())

    print(f"\n{'='*80}")
    print(f"Disk Usage Summary - {path}")
    print(f"{'='*80}")
    print(f"Total Size: {format_size(total_size)}")
    print(f"Folders: {len(breakdown)}\n")

    print_tree(breakdown)

    print(f"\n{'='*80}")

    # Generate reports
    create_json_report(breakdown, path)
    create_html_report(breakdown, path)

    # Try to open with Plotly if available
    if PLOTLY_AVAILABLE:
        try:
            sorted_folders = sorted(
                breakdown.items(), key=lambda x: x[1]["size"], reverse=True
            )

            # Sunburst chart
            def build_sunburst_data(bd, root_path=path):
                labels = []
                parents = []
                values = []
                ids = []
                formatted = []

                root_id = root_path

                # Add root node
                total_size = sum(item["size"] for item in bd.values())
                labels.append("Root")
                parents.append("")
                values.append(total_size)
                ids.append(root_id)
                formatted.append(format_size(total_size))

                # Recursive function to add nodes using unique ids (paths)
                def add_folder(folder_name, folder_data, parent_id):
                    node_id = folder_data.get("path") or f"{parent_id}/{folder_name}"
                    labels.append(folder_name)
                    parents.append(parent_id)
                    values.append(folder_data["size"])
                    ids.append(node_id)
                    formatted.append(format_size(folder_data["size"]))

                    # Recursively add subfolders
                    if folder_data["subdirs"]:
                        for subfolder_name, subfolder_data in folder_data[
                            "subdirs"
                        ].items():
                            add_folder(subfolder_name, subfolder_data, node_id)

                # Add all top-level folders
                for folder_name, folder_data in bd.items():
                    add_folder(folder_name, folder_data, root_id)

                return labels, parents, values, ids, formatted

            labels, parents, values, ids, formatted = build_sunburst_data(breakdown)

            if labels and len(labels) > 1 and ids and len(ids) == len(labels):
                fig = go.Figure(
                    go.Sunburst(
                        labels=labels,
                        ids=ids,
                        parents=parents,
                        values=values,
                        customdata=formatted,
                        marker=dict(colorscale="Blues"),
                        texttemplate="%{label}<br>%{customdata}",
                        textinfo="text",
                    )
                )
                fig.write_html("disk_usage_sunburst.html")
            print("✅ Interactive sunburst chart saved to: disk_usage_sunburst.html")
        except Exception as e:
            print(f"⚠️  Could not create Plotly chart: {e}")


def main_gui() -> None:
    """Run the simple Tkinter GUI for interactive analysis.

    The GUI allows the user to pick a folder and run the same analysis that
    the CLI performs, saving HTML/JSON reports to the current working
    directory.

    Returns:
        None
    """
    root = tk.Tk()
    root.title("Disk Usage Visualizer")
    root.geometry("500x300")

    selected_path = tk.StringVar(value=os.path.expanduser("~"))
    max_depth_var = tk.IntVar(value=2)

    def browse_folder():
        path = filedialog.askdirectory(title="Select a folder to analyze")
        if path:
            selected_path.set(path)

    def analyze():
        path = selected_path.get()
        if not os.path.isdir(path):
            messagebox.showerror("Error", f"Invalid path: {path}")
            return

        status_label.config(text="Analyzing... Please wait")
        root.update()

        try:
            breakdown = get_folder_breakdown(path, max_depth_var.get())
            create_json_report(breakdown, path)
            create_html_report(breakdown, path)

            if PLOTLY_AVAILABLE:
                # Similar to CLI
                pass

            messagebox.showinfo(
                "Success",
                "Analysis complete!\n\nReports saved:\n"
                "- disk_usage_report.html\n"
                "- disk_usage_report.json",
            )
            status_label.config(text="Analysis complete!")
        except Exception as e:
            messagebox.showerror("Error", f"Analysis failed: {e}")
            status_label.config(text="Error during analysis")

    # UI Elements
    tk.Label(root, text="Path:", font=("Arial", 10, "bold")).pack(pady=5)
    path_frame = tk.Frame(root)
    path_frame.pack(fill=tk.X, padx=10, pady=5)
    tk.Entry(path_frame, textvariable=selected_path, width=50).pack(
        side=tk.LEFT, fill=tk.X, expand=True
    )
    tk.Button(path_frame, text="Browse", command=browse_folder).pack(
        side=tk.LEFT, padx=5
    )

    tk.Label(root, text="Depth:", font=("Arial", 10, "bold")).pack(pady=5)
    tk.Scale(root, from_=1, to=5, orient=tk.HORIZONTAL, variable=max_depth_var).pack(
        fill=tk.X, padx=10
    )

    tk.Button(
        root,
        text="Analyze",
        command=analyze,
        bg="#667eea",
        fg="white",
        font=("Arial", 12, "bold"),
    ).pack(pady=20)

    status_label = tk.Label(root, text="Ready", fg="#666")
    status_label.pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # CLI mode with path argument
        main_cli(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2)
    elif "--gui" in sys.argv or "--ui" in sys.argv:
        # GUI mode
        main_gui()
    else:
        # Interactive mode
        print("Disk Usage Visualizer")
        print("=====================\n")
        print("1. CLI mode (command line)")
        print("2. GUI mode (graphical interface)\n")

        choice = input("Select mode (1 or 2): ").strip()

        if choice == "2":
            main_gui()
        else:
            main_cli()
