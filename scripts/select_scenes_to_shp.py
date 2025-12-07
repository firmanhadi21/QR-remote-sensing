#!/usr/bin/env python3
"""
Select PlanetScope scenes by cloud cover threshold and export footprints to Shapefile.

Usage:
    python select_scenes_to_shp.py [--cloud-max 50] [--output PSScene_selected]

Requirements:
    pip install pyshp
"""

import argparse
import json
import os
import shapefile


def select_scenes_to_shapefile(input_dir, output_name, cloud_max=50):
    """
    Select scenes with cloud cover below threshold and create a shapefile.

    Parameters:
        input_dir (str): Directory containing PlanetScope metadata files
        output_name (str): Output shapefile name (without extension)
        cloud_max (float): Maximum cloud cover percentage (0-100)

    Returns:
        int: Number of scenes selected
    """
    output_path = os.path.join(input_dir, output_name)

    # Create shapefile writer with polygon type
    w = shapefile.Writer(output_path)
    w.autoBalance = 1

    # Define fields
    w.field('scene_id', 'C', 40)
    w.field('acquired', 'C', 30)
    w.field('cloud_cov', 'N', 10, 2)
    w.field('clear_pct', 'N', 10, 2)
    w.field('gsd', 'N', 10, 2)
    w.field('satellite', 'C', 10)
    w.field('sun_elev', 'N', 10, 2)
    w.field('sun_az', 'N', 10, 2)
    w.field('view_angle', 'N', 10, 2)
    w.field('tif_file', 'C', 80)

    # Convert threshold to decimal (0-1)
    cloud_threshold = cloud_max / 100.0

    # Process all metadata files
    count = 0
    for f in sorted(os.listdir(input_dir)):
        if f.endswith('_metadata.json'):
            metadata_path = os.path.join(input_dir, f)
            with open(metadata_path, 'r') as fp:
                data = json.load(fp)

            # Get cloud cover (stored as decimal 0-1)
            props = data.get('properties', data)
            cloud_cover = props.get('cloud_cover', 1.0)

            # Filter by cloud cover threshold
            if cloud_cover <= cloud_threshold:
                # Get geometry from the corresponding STAC json
                base = f.replace('_metadata.json', '')
                stac_file = os.path.join(input_dir, base + '.json')

                if os.path.exists(stac_file):
                    with open(stac_file, 'r') as fp:
                        stac = json.load(fp)

                    geom = stac.get('geometry', data.get('geometry', {}))
                    coords = geom.get('coordinates', [[]])

                    if coords and coords[0]:
                        # Write polygon
                        w.poly([coords[0]])

                        # Write attributes
                        tif_file = f"{base}_3B_AnalyticMS_SR_file_format.tif"
                        w.record(
                            scene_id=base,
                            acquired=props.get('acquired', ''),
                            cloud_cov=cloud_cover * 100,  # Convert to percentage
                            clear_pct=props.get('clear_percent', 0),
                            gsd=props.get('gsd', 3.0),
                            satellite=props.get('satellite_id', ''),
                            sun_elev=props.get('sun_elevation', 0),
                            sun_az=props.get('sun_azimuth', 0),
                            view_angle=props.get('view_angle', 0),
                            tif_file=tif_file
                        )
                        count += 1

    w.close()

    # Create .prj file (WGS84 / EPSG:4326)
    prj_content = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]'
    prj_path = output_path + '.prj'
    with open(prj_path, 'w') as prj:
        prj.write(prj_content)

    return count


def main():
    parser = argparse.ArgumentParser(
        description='Select PlanetScope scenes by cloud cover and export to Shapefile'
    )
    parser.add_argument(
        '--input-dir', '-i',
        default='.',
        help='Input directory containing PlanetScope metadata files (default: current directory)'
    )
    parser.add_argument(
        '--cloud-max', '-c',
        type=float,
        default=50,
        help='Maximum cloud cover percentage (default: 50)'
    )
    parser.add_argument(
        '--output', '-o',
        default='PSScene_selected',
        help='Output shapefile name without extension (default: PSScene_selected)'
    )

    args = parser.parse_args()

    # Run selection
    count = select_scenes_to_shapefile(
        input_dir=args.input_dir,
        output_name=args.output,
        cloud_max=args.cloud_max
    )

    # Report results
    print(f"Selected {count} scenes with cloud cover <= {args.cloud_max}%")
    print(f"\nOutput files:")
    for ext in ['.shp', '.shx', '.dbf', '.prj']:
        fpath = os.path.join(args.input_dir, args.output + ext)
        if os.path.exists(fpath):
            size = os.path.getsize(fpath)
            print(f"  {args.output}{ext} ({size:,} bytes)")


if __name__ == '__main__':
    main()
