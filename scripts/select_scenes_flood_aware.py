#!/usr/bin/env python3
"""
Select PlanetScope scenes for flood assessment using cloud cover and water detection.

Filtering logic:
- Accept scenes with cloud cover <= 80%
- Accept scenes with cloud cover > 80% IF water is detected
- Reject scenes with cloud cover > 80% AND no water detected

Water detection uses NIR band (low NIR reflectance indicates water).

Usage:
    python select_scenes_flood_aware.py [--cloud-max 80] [--water-threshold 1000]
                                        [--min-water-pct 1.0] [--output PSScene_flood]

Requirements:
    pip install pyshp numpy
    GDAL Python bindings (osgeo)
"""

import argparse
import json
import os
import sys
import numpy as np
from osgeo import gdal
import shapefile


def detect_water_extent(tif_path, udm2_path, nir_threshold=1000):
    """
    Detect water extent in a PlanetScope scene using NIR band.

    Parameters:
        tif_path (str): Path to AnalyticMS_SR TIFF file
        udm2_path (str): Path to UDM2 file
        nir_threshold (int): NIR threshold for water (0-10000 scale, default: 1000)

    Returns:
        dict: {
            'water_pct': float,      # Percentage of clear pixels that are water
            'clear_pct': float,      # Percentage of valid pixels that are clear
            'water_pixels': int,
            'clear_pixels': int,
            'total_pixels': int
        }
    """
    result = {
        'water_pct': 0.0,
        'clear_pct': 0.0,
        'water_pixels': 0,
        'clear_pixels': 0,
        'total_pixels': 0
    }

    # Check if files exist
    if not os.path.exists(tif_path):
        print(f"  WARNING: TIFF not found: {os.path.basename(tif_path)}")
        return result

    if not os.path.exists(udm2_path):
        print(f"  WARNING: UDM2 not found: {os.path.basename(udm2_path)}")
        return result

    try:
        # Open the AnalyticMS_SR file and read NIR band (band 4)
        ds = gdal.Open(tif_path, gdal.GA_ReadOnly)
        if ds is None:
            print(f"  ERROR: Cannot open {os.path.basename(tif_path)}")
            return result

        nir_band = ds.GetRasterBand(4)
        nir_data = nir_band.ReadAsArray()
        ds = None  # Close dataset

        # Open UDM2 file and read clear (band 1) and cloud (band 6) masks
        udm2_ds = gdal.Open(udm2_path, gdal.GA_ReadOnly)
        if udm2_ds is None:
            print(f"  ERROR: Cannot open {os.path.basename(udm2_path)}")
            return result

        clear_band = udm2_ds.GetRasterBand(1)
        cloud_band = udm2_ds.GetRasterBand(6)

        clear_mask = clear_band.ReadAsArray()
        cloud_mask = cloud_band.ReadAsArray()
        udm2_ds = None  # Close dataset

        # Calculate masks
        total_pixels = nir_data.size

        # Clear pixels: clear=1 AND cloud=0 AND nir!=0 (valid data)
        clear_pixels_mask = (clear_mask == 1) & (cloud_mask == 0) & (nir_data > 0)
        clear_pixels = np.sum(clear_pixels_mask)

        # Water pixels: clear AND NIR < threshold
        water_pixels_mask = clear_pixels_mask & (nir_data < nir_threshold)
        water_pixels = np.sum(water_pixels_mask)

        # Calculate percentages
        if total_pixels > 0:
            result['clear_pct'] = (clear_pixels / total_pixels) * 100

        if clear_pixels > 0:
            result['water_pct'] = (water_pixels / clear_pixels) * 100

        result['water_pixels'] = int(water_pixels)
        result['clear_pixels'] = int(clear_pixels)
        result['total_pixels'] = int(total_pixels)

    except Exception as e:
        print(f"  ERROR processing {os.path.basename(tif_path)}: {e}")

    return result


def select_scenes_flood_aware(input_dir, output_name, cloud_max=80,
                               nir_threshold=1000, min_water_pct=1.0):
    """
    Select scenes for flood assessment with water detection.

    Parameters:
        input_dir (str): Directory containing PlanetScope data
        output_name (str): Output shapefile name (without extension)
        cloud_max (float): Maximum cloud cover percentage for automatic acceptance
        nir_threshold (int): NIR threshold for water detection (0-10000 scale)
        min_water_pct (float): Minimum water percentage to accept high-cloud scenes

    Returns:
        dict: Selection statistics
    """
    output_path = os.path.join(input_dir, output_name)

    # Create shapefile writer
    w = shapefile.Writer(output_path)
    w.autoBalance = 1

    # Define fields
    w.field('scene_id', 'C', 40)
    w.field('acquired', 'C', 30)
    w.field('cloud_cov', 'N', 10, 2)
    w.field('clear_pct', 'N', 10, 2)
    w.field('water_pct', 'N', 10, 2)
    w.field('gsd', 'N', 10, 2)
    w.field('satellite', 'C', 10)
    w.field('sun_elev', 'N', 10, 2)
    w.field('sun_az', 'N', 10, 2)
    w.field('view_angle', 'N', 10, 2)
    w.field('tif_file', 'C', 80)
    w.field('selection', 'C', 20)  # Reason for selection

    # Statistics
    stats = {
        'total_scenes': 0,
        'accepted': 0,
        'rejected': 0,
        'low_cloud_accept': 0,
        'high_cloud_water_accept': 0,
        'high_cloud_no_water_reject': 0
    }

    # Process all metadata files
    metadata_files = sorted([f for f in os.listdir(input_dir) if f.endswith('_metadata.json')])

    print(f"\nProcessing {len(metadata_files)} scenes...")
    print(f"Cloud threshold: {cloud_max}%")
    print(f"NIR threshold: {nir_threshold} (0-10000 scale)")
    print(f"Minimum water: {min_water_pct}%")
    print("-" * 80)

    for f in metadata_files:
        stats['total_scenes'] += 1
        metadata_path = os.path.join(input_dir, f)

        with open(metadata_path, 'r') as fp:
            data = json.load(fp)

        # Get cloud cover
        props = data.get('properties', data)
        cloud_cover = props.get('cloud_cover', 1.0) * 100  # Convert to percentage

        # Get file paths
        base = f.replace('_metadata.json', '')
        stac_file = os.path.join(input_dir, base + '.json')
        tif_file = os.path.join(input_dir, base + '_3B_AnalyticMS_SR_file_format.tif')
        udm2_file = os.path.join(input_dir, base + '_3B_udm2_file_format.tif')

        # Detect water extent
        water_info = detect_water_extent(tif_file, udm2_file, nir_threshold)

        # Determine selection
        selected = False
        selection_reason = ""

        if cloud_cover <= cloud_max:
            # Accept all scenes with acceptable cloud cover
            selected = True
            selection_reason = "low_cloud"
            stats['low_cloud_accept'] += 1
        else:
            # High cloud cover: check for water
            if water_info['water_pct'] >= min_water_pct:
                selected = True
                selection_reason = "high_cloud_water"
                stats['high_cloud_water_accept'] += 1
            else:
                selected = False
                selection_reason = "high_cloud_no_water"
                stats['high_cloud_no_water_reject'] += 1

        # Print status
        status = "✓ ACCEPT" if selected else "✗ REJECT"
        print(f"{status} {base}")
        print(f"  Cloud: {cloud_cover:5.1f}% | Water: {water_info['water_pct']:5.2f}% | "
              f"Clear: {water_info['clear_pct']:5.1f}% | Reason: {selection_reason}")

        # If selected, add to shapefile
        if selected:
            stats['accepted'] += 1

            # Get geometry
            if os.path.exists(stac_file):
                with open(stac_file, 'r') as fp:
                    stac = json.load(fp)

                geom = stac.get('geometry', data.get('geometry', {}))
                coords = geom.get('coordinates', [[]])

                if coords and coords[0]:
                    # Write polygon
                    w.poly([coords[0]])

                    # Write attributes
                    w.record(
                        scene_id=base,
                        acquired=props.get('acquired', ''),
                        cloud_cov=cloud_cover,
                        clear_pct=water_info['clear_pct'],
                        water_pct=water_info['water_pct'],
                        gsd=props.get('gsd', 3.0),
                        satellite=props.get('satellite_id', ''),
                        sun_elev=props.get('sun_elevation', 0),
                        sun_az=props.get('sun_azimuth', 0),
                        view_angle=props.get('view_angle', 0),
                        tif_file=base + '_3B_AnalyticMS_SR_file_format.tif',
                        selection=selection_reason
                    )
        else:
            stats['rejected'] += 1

    w.close()

    # Create .prj file (WGS84 / EPSG:4326)
    prj_content = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]'
    prj_path = output_path + '.prj'
    with open(prj_path, 'w') as prj:
        prj.write(prj_content)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Select PlanetScope scenes for flood assessment with water detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Filtering Logic:
  - Scenes with cloud cover <= CLOUD_MAX are automatically accepted
  - Scenes with cloud cover > CLOUD_MAX are accepted only if water >= MIN_WATER_PCT
  - This ensures high-cloud scenes containing flood areas are not rejected

Water Detection:
  - Uses NIR band (band 4) from AnalyticMS_SR product
  - Water has low NIR reflectance (< NIR_THRESHOLD)
  - Only clear pixels (not cloud/shadow) are analyzed using UDM2 masks
        """
    )
    parser.add_argument(
        '--input-dir', '-i',
        default='.',
        help='Input directory containing PlanetScope data (default: current directory)'
    )
    parser.add_argument(
        '--cloud-max', '-c',
        type=float,
        default=80,
        help='Maximum cloud cover percentage for automatic acceptance (default: 80)'
    )
    parser.add_argument(
        '--nir-threshold', '-n',
        type=int,
        default=1000,
        help='NIR threshold for water detection, 0-10000 scale (default: 1000 = 10%% reflectance)'
    )
    parser.add_argument(
        '--min-water-pct', '-w',
        type=float,
        default=1.0,
        help='Minimum water percentage to accept high-cloud scenes (default: 1.0%%)'
    )
    parser.add_argument(
        '--output', '-o',
        default='PSScene_flood',
        help='Output shapefile name without extension (default: PSScene_flood)'
    )

    args = parser.parse_args()

    # Validate input directory
    if not os.path.isdir(args.input_dir):
        print(f"ERROR: Input directory not found: {args.input_dir}")
        sys.exit(1)

    # Run selection
    print("=" * 80)
    print("PlanetScope Scene Selection - Flood-Aware")
    print("=" * 80)

    stats = select_scenes_flood_aware(
        input_dir=args.input_dir,
        output_name=args.output,
        cloud_max=args.cloud_max,
        nir_threshold=args.nir_threshold,
        min_water_pct=args.min_water_pct
    )

    # Report results
    print("\n" + "=" * 80)
    print("SELECTION SUMMARY")
    print("=" * 80)
    print(f"Total scenes processed:           {stats['total_scenes']}")
    print(f"  ✓ Accepted:                     {stats['accepted']}")
    print(f"    - Low cloud (<= {args.cloud_max}%):        {stats['low_cloud_accept']}")
    print(f"    - High cloud with water:      {stats['high_cloud_water_accept']}")
    print(f"  ✗ Rejected:                     {stats['rejected']}")
    print(f"    - High cloud without water:   {stats['high_cloud_no_water_reject']}")
    print("\nOutput files:")
    for ext in ['.shp', '.shx', '.dbf', '.prj']:
        fpath = os.path.join(args.input_dir, args.output + ext)
        if os.path.exists(fpath):
            size = os.path.getsize(fpath)
            print(f"  {args.output}{ext} ({size:,} bytes)")
    print("=" * 80)


if __name__ == '__main__':
    main()
