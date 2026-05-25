import os

import plotly.graph_objects as go
import streamlit as st

from functions import (
    build_sunburst_data,
    format_size,
    get_folder_breakdown,
    get_windows_drives,
)

st.set_page_config(page_title="Disk Usage Visualizer", layout="wide")

st.title("💾 Disk Usage Visualizer")
st.write("Explore disk usage across your folders and subfolders")

# Get available drives on Windows (delegated to core.get_windows_drives)

# Helper functions are provided in `functions.py` (imported above)

# Sidebar for path selection
st.sidebar.header("📁 Path Selection")

# Option to choose drive
drives = get_windows_drives()
selected_drive = st.sidebar.selectbox("Select Drive:", drives, key="drive_select")

# Manual path input
custom_path = st.sidebar.text_input("Or enter a custom path:", value=selected_drive)

# Validate path
if os.path.isdir(custom_path):
    selected_path = custom_path
else:
    st.error(f"❌ Invalid path: {custom_path}")
    st.stop()

# Depth selection
max_depth = st.sidebar.slider("Folder depth to analyze:", 1, 5, 2)

# Show current path
st.sidebar.info(f"📍 Current Path: {selected_path}")

# Analysis button
if st.sidebar.button("🔍 Analyze", use_container_width=True):
    st.session_state.analyze = True
else:
    st.session_state.analyze = st.session_state.get('analyze', False)

# Main content
if st.session_state.analyze:
    with st.spinner("Analyzing folder structure..."):
        folder_breakdown = get_folder_breakdown(selected_path, max_depth)
    
    if not folder_breakdown:
        st.warning("No subfolders found or access denied.")
    else:
        # Create sorted list for visualization
        sorted_folders = sorted(
            folder_breakdown.items(),
            key=lambda x: x[1]['size'],
            reverse=True
        )
        
        # Calculate total size
        total_size = sum(item[1]['size'] for item in sorted_folders)
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Size", format_size(total_size))
        with col2:
            st.metric("Folders Analyzed", len(sorted_folders))
        with col3:
            largest_folder = sorted_folders[0] if sorted_folders else None
            if largest_folder:
                st.metric("Largest Folder", format_size(largest_folder[1]['size']))
        
        # Visualization 1: Sunburst Chart
        st.subheader("🔆 Sunburst Chart View")

        # Build sunburst arrays using the shared `functions` implementation
        labels, parents, values, ids, formatted_sizes = build_sunburst_data(
            folder_breakdown, selected_path
        )

        # Debug output for sunburst data
        try:
            total_values = sum(values) if values else 0
        except Exception:
            total_values = None

        # st.markdown("**Sunburst debug info**")
        # st.write({
        #     "labels_count": len(labels),
        #     "parents_count": len(parents),
        #     "values_count": len(values),
        #     "ids_count": len(ids),
        #     "values_sum_bytes": total_values
        # })

        # # Show a small sample to inspect structure
        # sample = list(zip(ids, labels, parents, values, formatted_sizes))[:40]
        # st.write(sample)

        # Basic validation
        valid = True
        if not (len(labels) == len(parents) == len(values) == len(ids)):
            st.error("Sunburst data arrays have mismatched lengths; chart will not render.")
            valid = False

        if total_values in (0, None):
            st.warning("Sunburst values sum to zero or could not be computed; chart may be empty.")

        # Ensure all parent id references exist (allow empty string for root)
        missing_parents = [p for p in set(parents) if p and p not in ids]
        if missing_parents:
            st.error(f"Parents referencing missing ids: {missing_parents}")
            valid = False

        if valid and labels and len(labels) > 1 and total_values and total_values > 0:
            fig_sunburst = go.Figure(go.Sunburst(
                labels=labels,
                ids=ids,
                parents=parents,
                values=values,
                customdata=formatted_sizes,
                marker=dict(colorscale="Blues"),
                texttemplate="%{label}<br>%{customdata}",
                textinfo="text"
            ))

            fig_sunburst.update_layout(
                height=600,
                font=dict(size=12)
            )
            st.plotly_chart(fig_sunburst, use_container_width=True)
        else:
            st.info("Not enough valid data to display sunburst chart. Check debug output above.")
        
        # Visualization 2: Bar Chart (Top folders)
        st.subheader("📊 Top Folders by Size")
        
        top_n = st.slider("Show top N folders:", 5, 20, 10)
        top_folders = sorted_folders[:top_n]
        
        folder_names = [f[0] for f in top_folders]
        folder_sizes = [f[1]['size'] / (1024**3) for f in top_folders]  # Convert to GB
        
        fig_bar = go.Figure(data=[
            go.Bar(
                x=folder_names,
                y=folder_sizes,
                marker=dict(color=folder_sizes, colorscale="Viridis"),
                text=[format_size(f[1]['size']) for f in top_folders],
                textposition="outside"
            )
        ])
        
        fig_bar.update_layout(
            title="Top Folders by Size",
            xaxis_title="Folder Name",
            yaxis_title="Size (GB)",
            height=400,
            xaxis_tickangle=-45
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Visualization 3: Detailed Table
        st.subheader("📋 Detailed Folder Breakdown")
        
        table_data = []
        for folder_name, folder_data in sorted_folders:
            percentage = (folder_data['size'] / total_size * 100) if total_size > 0 else 0
            table_data.append({
                "Folder Name": folder_name,
                "Size": format_size(folder_data['size']),
                "Size (GB)": f"{folder_data['size'] / (1024**3):.2f}",
                "Percentage": f"{percentage:.1f}%",
                "Path": folder_data['path']
            })
        
        st.dataframe(table_data, use_container_width=True)
        
        # Download summary
        st.subheader("📥 Export Summary")
        
        import json
        summary_json = json.dumps({
            "root_path": selected_path,
            "total_size": total_size,
            "total_size_formatted": format_size(total_size),
            "folders": [
                {
                    "name": name,
                    "size": data['size'],
                    "size_formatted": format_size(data['size']),
                    "path": data['path']
                }
                for name, data in sorted_folders
            ]
        }, indent=2)
        
        st.download_button(
            label="Download as JSON",
            data=summary_json,
            file_name="disk_usage_summary.json",
            mime="application/json"
        )
else:
    st.info("👈 Select a path on the left sidebar and click 'Analyze' to get started!")
