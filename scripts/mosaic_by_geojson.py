#!/usr/bin/env python3
"""
Filter PlanetScope scenes by GeoJSON boundary and generate mosaic script.

This script:
1. Reads a shapefile with scene footprints
2. Reads a GeoJSON file with area of interest (AOI)
3. Filters scenes that intersect with the AOI
4. Clusters filtered scenes by spatial proximity
5. Generates an OrfeoToolbox mosaic script

Usage:
    python mosaic_by_geojson.py --shapefile PSScene_flood_aware.shp \
                                 --geojson sumbar1.geojson \
                                 --data-dir /path/to/tiff/files \
                                 --output-script mosaic_sumbar1.sh

Requirements:
    pip install pyshp numpy scikit-learn scipy shapely
"""

import argparse
import json
import os
import sys
import shapefile
import numpy as np
from sklearn.cluster import DBSCAN
from shapely.geometry import shape, Polygon


def read_geojson_boundary(geojson_path):
    """
    Read GeoJSON file and return boundary polygon(s).

    Returns:
        Shapely geometry object
    """
    with open(geojson_path, 'r') as f:
        geojson_data = json.load(f)

    # Handle FeatureCollection or single Feature
    if geojson_data['type'] == 'FeatureCollection':
        # Union all features
        geometries = [shape(feature['geometry']) for feature in geojson_data['features']]
        if len(geometries) == 1:
            return geometries[0]
        else:
            from shapely.ops import unary_union
            return unary_union(geometries)
    elif geojson_data['type'] == 'Feature':
        return shape(geojson_data['geometry'])
    else:
        # Direct geometry
        return shape(geojson_data)


def read_shapefile_scenes(shp_path):
    """
    Read scene information from shapefile including geometry.

    Returns:
        list of dict: Scene information with Shapely polygon
    """
    scenes = []

    sf = shapefile.Reader(shp_path)
    fields = [f[0] for f in sf.fields[1:]]  # Skip deletion flag

    for shape_rec in sf.shapeRecords():
        record = dict(zip(fields, shape_rec.record))
        shape_obj = shape_rec.shape

        # Get points and create Shapely polygon
        points = shape_obj.points
        polygon = Polygon(points)

        # Calculate centroid
        centroid = polygon.centroid

        # Calculate bounding box size
        bounds = polygon.bounds
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]

        scenes.append({
            'scene_id': record.get('scene_id', ''),
            'tif_file': record.get('tif_file', ''),
            'cloud_cov': float(record.get('cloud_cov', 0)),
            'water_pct': float(record.get('water_pct', 0)) if 'water_pct' in record else 0,
            'centroid': (centroid.x, centroid.y),
            'bbox_size': (width, height),
            'polygon': polygon,
            'geometry': points
        })

    return scenes


def filter_scenes_by_boundary(scenes, boundary):
    """
    Filter scenes that intersect with the boundary.

    Parameters:
        scenes (list): List of scene dictionaries with 'polygon' key
        boundary: Shapely geometry object

    Returns:
        list: Filtered scenes
    """
    filtered = []

    for scene in scenes:
        if scene['polygon'].intersects(boundary):
            filtered.append(scene)

    return filtered


def cluster_scenes(scenes, eps_factor=1.5, min_samples=2):
    """
    Cluster scenes based on spatial proximity using DBSCAN.

    Parameters:
        scenes (list): List of scene dictionaries
        eps_factor (float): Distance threshold as multiple of average scene size
        min_samples (int): Minimum scenes per cluster

    Returns:
        dict: Clusters with scene lists
    """
    if not scenes:
        return {}

    # Extract centroids
    centroids = np.array([s['centroid'] for s in scenes])

    # Calculate average scene size to determine clustering distance
    avg_width = np.mean([s['bbox_size'][0] for s in scenes])
    avg_height = np.mean([s['bbox_size'][1] for s in scenes])
    avg_size = (avg_width + avg_height) / 2

    # Use eps as multiple of average scene size
    eps = eps_factor * avg_size

    print(f"\nClustering parameters:")
    print(f"  Average scene size: {avg_size:.6f} degrees")
    print(f"  Clustering distance (eps): {eps:.6f} degrees ({eps_factor}x scene size)")
    print(f"  Minimum samples per cluster: {min_samples}")

    # Perform DBSCAN clustering
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean')
    labels = clustering.fit_predict(centroids)

    # Organize scenes by cluster
    clusters = {}
    noise_count = 0

    for scene, label in zip(scenes, labels):
        if label == -1:
            # Noise/outlier - create individual cluster
            noise_count += 1
            cluster_id = f"single_{noise_count}"
        else:
            cluster_id = f"cluster_{label + 1}"

        if cluster_id not in clusters:
            clusters[cluster_id] = []

        clusters[cluster_id].append(scene)

    # Sort scenes within each cluster by cloud cover (highest first)
    for cluster_id in clusters:
        clusters[cluster_id].sort(key=lambda s: s['cloud_cov'], reverse=True)

    return clusters


def generate_mosaic_script(clusters, data_dir, output_script, aoi_name, otb_path=None):
    """
    Generate bash script for mosaicking clusters using OrfeoToolbox.

    Parameters:
        clusters (dict): Clustered scenes
        data_dir (str): Directory containing TIFF files
        output_script (str): Output bash script path
        aoi_name (str): Name of the AOI for output naming
        otb_path (str): Path to OTB mosaic binary (optional)
    """
    if otb_path is None:
        otb_path = "/Users/macbook/OTB-8.1.2-Darwin64/bin/otbcli_Mosaic"

    output_dir = os.path.join(data_dir, f"mosaic_{aoi_name}")

    script_lines = [
        "#!/bin/bash",
        "#",
        f"# Auto-generated mosaic script for {aoi_name}",
        "# Scenes filtered by GeoJSON boundary and clustered spatially",
        "#",
        "",
        "# Configuration",
        f'OTB_MOSAIC="{otb_path}"',
        f'INPUT_DIR="{data_dir}"',
        f'OUTPUT_DIR="{output_dir}"',
        "",
        "# Create output directory",
        'mkdir -p "$OUTPUT_DIR"',
        "",
        'echo "=========================================="',
        f'echo "PlanetScope Mosaic - {aoi_name}"',
        'echo "Scenes ordered by cloud cover (highest first = bottom)"',
        'echo "=========================================="',
        'echo "Input directory: $INPUT_DIR"',
        'echo "Output directory: $OUTPUT_DIR"',
        'echo ""',
        "",
        "# Function to mosaic a cluster",
        "mosaic_cluster() {",
        "    local cluster=$1",
        "    shift",
        '    local files=("$@")',
        "",
        '    echo "Processing Cluster $cluster (${#files[@]} scenes)..."',
        "",
        "    # Build input list",
        '    local input_files=""',
        '    for f in "${files[@]}"; do',
        '        input_files="$input_files \\"$INPUT_DIR/$f\\""',
        "    done",
        "",
        '    local output_file="$OUTPUT_DIR/mosaic_${cluster}.tif"',
        "",
        "    # Run OTB Mosaic",
        '    eval "$OTB_MOSAIC" \\',
        "        -il $input_files \\",
        '        -out "\\"$output_file\\"" uint16 \\',
        "        -comp.feather large \\",
        "        -harmo.method band \\",
        "        -harmo.cost rmse \\",
        "        -interpolator nn \\",
        "        -nodata 0 \\",
        '        2>&1 | grep -v "^WARN"',
        "",
        '    if [ -f "$output_file" ]; then',
        '        echo "  -> Created: $output_file"',
        "    else",
        '        echo "  -> ERROR creating mosaic for cluster $cluster"',
        "    fi",
        '    echo ""',
        "}",
        ""
    ]

    # Sort clusters by size (largest first) and generate mosaic calls
    sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)

    for cluster_id, cluster_scene_list in sorted_clusters:
        # Generate comment with cluster info
        scene_count = len(cluster_scene_list)
        cloud_range = f"{max(s['cloud_cov'] for s in cluster_scene_list):.0f}% -> {min(s['cloud_cov'] for s in cluster_scene_list):.0f}%"

        script_lines.append(f"# {cluster_id}: {scene_count} scenes (cloud cover: {cloud_range})")

        # Generate mosaic call
        script_lines.append(f"mosaic_cluster {cluster_id} \\")

        for i, scene in enumerate(cluster_scene_list):
            tif_file = scene['tif_file']
            if i < len(cluster_scene_list) - 1:
                script_lines.append(f'    "{tif_file}" \\')
            else:
                script_lines.append(f'    "{tif_file}"')

        script_lines.append("")

    # Add completion message
    script_lines.extend([
        'echo "=========================================="',
        'echo "Mosaic complete!"',
        'echo "Output files in: $OUTPUT_DIR"',
        'ls -lh "$OUTPUT_DIR"/mosaic_*.tif 2>/dev/null || echo "No output files found"',
        'echo "=========================================="',
        ""
    ])

    # Write script
    with open(output_script, 'w') as f:
        f.write('\n'.join(script_lines))

    # Make executable
    os.chmod(output_script, 0o755)

    return sorted_clusters


def main():
    parser = argparse.ArgumentParser(
        description='Filter scenes by GeoJSON boundary and generate mosaic script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Workflow:
  1. Reads shapefile with all available scenes
  2. Reads GeoJSON file with area of interest (AOI) boundary
  3. Filters scenes that intersect with the AOI
  4. Clusters filtered scenes spatially using DBSCAN
  5. Generates mosaic script with clusters ordered by cloud cover

Example:
  python mosaic_by_geojson.py \\
    --shapefile PSScene/PSScene_flood_aware.shp \\
    --geojson sumbar1.geojson \\
    --data-dir . \\
    --output-script PSScene/mosaic_sumbar1.sh
        """
    )

    parser.add_argument(
        '--shapefile', '-s',
        required=True,
        help='Input shapefile with scene footprints'
    )
    parser.add_argument(
        '--geojson', '-g',
        required=True,
        help='GeoJSON file with area of interest boundary'
    )
    parser.add_argument(
        '--data-dir', '-d',
        required=True,
        help='Directory containing PlanetScope TIFF files'
    )
    parser.add_argument(
        '--output-script', '-o',
        required=True,
        help='Output mosaic script filename'
    )
    parser.add_argument(
        '--otb-path',
        help='Path to otbcli_Mosaic binary (default: /Users/macbook/OTB-8.1.2-Darwin64/bin/otbcli_Mosaic)'
    )
    parser.add_argument(
        '--eps-factor',
        type=float,
        default=1.5,
        help='Clustering distance as multiple of scene size (default: 1.5)'
    )
    parser.add_argument(
        '--min-samples',
        type=int,
        default=2,
        help='Minimum scenes per cluster (default: 2)'
    )

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.shapefile):
        print(f"ERROR: Shapefile not found: {args.shapefile}")
        sys.exit(1)

    if not os.path.exists(args.geojson):
        print(f"ERROR: GeoJSON file not found: {args.geojson}")
        sys.exit(1)

    if not os.path.isdir(args.data_dir):
        print(f"ERROR: Data directory not found: {args.data_dir}")
        sys.exit(1)

    # Extract AOI name from geojson filename
    aoi_name = os.path.splitext(os.path.basename(args.geojson))[0]

    print("=" * 80)
    print(f"PlanetScope Mosaic Generation for {aoi_name}")
    print("=" * 80)

    # Read GeoJSON boundary
    print(f"\nReading boundary from: {args.geojson}")
    boundary = read_geojson_boundary(args.geojson)
    print(f"  Boundary loaded: {boundary.geom_type}")
    print(f"  Area: {boundary.area:.6f} square degrees")

    # Read scenes from shapefile
    print(f"\nReading scenes from: {args.shapefile}")
    all_scenes = read_shapefile_scenes(args.shapefile)
    print(f"  Total scenes available: {len(all_scenes)}")

    # Filter scenes by boundary
    print(f"\nFiltering scenes by boundary intersection...")
    filtered_scenes = filter_scenes_by_boundary(all_scenes, boundary)
    print(f"  Scenes within boundary: {len(filtered_scenes)}")

    if not filtered_scenes:
        print("\nERROR: No scenes intersect with the boundary!")
        print("Check that:")
        print("  1. GeoJSON and shapefile use the same coordinate system")
        print("  2. The boundary overlaps with the scene footprints")
        sys.exit(1)

    # Cluster scenes
    print("\nClustering scenes by spatial proximity...")
    clusters = cluster_scenes(filtered_scenes, eps_factor=args.eps_factor, min_samples=args.min_samples)

    # Print cluster summary
    print(f"\nCluster Summary:")
    print(f"  Total clusters: {len(clusters)}")

    sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)
    for cluster_id, cluster_scene_list in sorted_clusters:
        scene_count = len(cluster_scene_list)
        cloud_min = min(s['cloud_cov'] for s in cluster_scene_list)
        cloud_max = max(s['cloud_cov'] for s in cluster_scene_list)
        water_avg = sum(s['water_pct'] for s in cluster_scene_list) / scene_count

        print(f"  {cluster_id}: {scene_count} scenes | "
              f"Cloud: {cloud_max:.0f}%-{cloud_min:.0f}% | "
              f"Avg Water: {water_avg:.1f}%")

    # Generate mosaic script
    print(f"\nGenerating mosaic script: {args.output_script}")
    generate_mosaic_script(clusters, args.data_dir, args.output_script, aoi_name, args.otb_path)

    print("\n" + "=" * 80)
    print("SUCCESS!")
    print("=" * 80)
    print(f"Generated script: {args.output_script}")
    print(f"AOI: {aoi_name}")
    print(f"Filtered scenes: {len(filtered_scenes)} (from {len(all_scenes)} total)")
    print(f"Clusters created: {len(clusters)}")
    print("\nTo run mosaicking:")
    print(f"  {args.output_script}")
    print("=" * 80)


if __name__ == '__main__':
    main()
