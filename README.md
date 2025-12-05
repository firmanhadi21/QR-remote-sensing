# README

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Quick Response - Remote Sensing: A toolkit for processing PlanetScope satellite imagery, focusing on filtering scenes by cloud cover and water detection for flood assessment in Quick Response operations.

## Core Workflow

The repository implements a two-stage processing pipeline for PlanetScope imagery:

1. **Scene Selection**: Filters PlanetScope scenes and exports footprints to shapefile
   - `select_scenes_to_shp.py`: Simple cloud cover filtering
   - `select_scenes_flood_aware.py`: Flood-aware filtering with NIR-based water detection
2. **Mosaic Generation** (`mosaic_by_block.sh`): Creates mosaics of selected scenes grouped by geographic blocks, with cloud-cover-based ordering (highest cloud = bottom layer)

## Key Scripts

### select_scenes_to_shp.py

Python script that processes PlanetScope metadata to create shapefiles of selected scenes.

**Usage:**
```bash
python select_scenes_to_shp.py --input-dir . --cloud-max 50 --output PSScene_selected
```

**Dependencies:**
```bash
pip install pyshp
```

**Input Data Structure:**
- Expects `*_metadata.json` files containing PlanetScope scene metadata (cloud_cover, acquired date, sensor properties)
- Expects corresponding `.json` STAC files containing geometry information
- Scene naming convention: `YYYYMMDD_HHMMSS_XX_XXXX` (timestamp + satellite identifiers)

**Output:**
- Shapefile (.shp, .shx, .dbf, .prj) with WGS84 projection (EPSG:4326)
- Attributes: scene_id, acquired, cloud_cov, clear_pct, gsd, satellite, sun_elev, sun_az, view_angle, tif_file

**Important Details:**
- Cloud cover in metadata files is stored as decimal (0-1), converted to percentage (0-100) in output
- References expected TIFF filename format: `{scene_id}_3B_AnalyticMS_SR_file_format.tif`

### select_scenes_flood_aware.py

**RECOMMENDED FOR FLOOD ASSESSMENT**: Enhanced scene selection script with NIR-based water detection to avoid rejecting high-cloud scenes that contain flood areas.

**Usage:**
```bash
python select_scenes_flood_aware.py --input-dir . --cloud-max 80 \
                                    --nir-threshold 1000 --min-water-pct 1.0 \
                                    --output PSScene_flood
```

**Dependencies:**
```bash
pip install pyshp numpy
# GDAL Python bindings (osgeo) - usually installed with GDAL/OTB
```

**Filtering Logic:**
- Scenes with cloud cover ≤ `cloud-max` (default 80%) are automatically accepted
- Scenes with cloud cover > `cloud-max` are accepted ONLY if water extent ≥ `min-water-pct` (default 1%)
- This ensures high-cloud scenes containing flood areas are not rejected

**Water Detection Algorithm:**
1. Reads NIR band (band 4) from `*_3B_AnalyticMS_SR_file_format.tif`
2. Reads clear and cloud masks from `*_3B_udm2_file_format.tif` (bands 1 and 6)
3. Identifies clear pixels: UDM2 clear=1 AND cloud=0 AND NIR>0
4. Detects water: Clear pixels with NIR < `nir-threshold` (default 1000 = 10% reflectance)
5. Calculates water percentage: water_pixels / clear_pixels × 100

**PlanetScope Band Structure:**
- **AnalyticMS_SR** (UInt16, Surface Reflectance 0-10000 scale):
  - Band 1: Blue
  - Band 2: Green
  - Band 3: Red
  - Band 4: NIR (used for water detection)
- **UDM2** (Byte, 0=false/1=true masks):
  - Band 1: clear
  - Band 6: cloud
  - Other bands: snow, shadow, haze_light, haze_heavy, confidence, udm1

**Output Shapefile Attributes:**
- All attributes from `select_scenes_to_shp.py` plus:
- `water_pct`: Percentage of clear pixels identified as water
- `selection`: Reason for selection (low_cloud / high_cloud_water)

**Tuning Parameters:**
- `--nir-threshold`: Lower values = more sensitive water detection (default 1000 works well for flood assessment)
- `--min-water-pct`: Minimum water percentage to accept high-cloud scenes (default 1.0% = at least some water present)
- `--cloud-max`: Maximum cloud cover for automatic acceptance (default 80%)

### mosaic_by_block.sh

Bash script using OrfeoToolbox to mosaic PlanetScope scenes by geographic blocks.

**Usage:**
```bash
./mosaic_by_block.sh
```

**Configuration (hardcoded in script):**
- `OTB_MOSAIC`: Path to otbcli_Mosaic binary
- `INPUT_DIR`: Directory containing input TIFF files
- `OUTPUT_DIR`: Directory for mosaic outputs

**Prerequisites:**
- OrfeoToolbox installed (tested with OTB-8.1.2)

**Mosaic Parameters:**
- Output format: uint16
- Feathering: large
- Harmonization method: band
- Harmonization cost: rmse
- Interpolator: nearest neighbor (nn)
- No-data value: 0

**Processing Strategy:**
- Scenes within each block are ordered by cloud cover (highest to lowest)
- Higher cloud cover scenes are placed at the bottom (rendered first)
- Lower cloud cover scenes are placed on top (rendered last)
- This ensures clearest pixels are visible in final mosaic

## Data Conventions

**PlanetScope File Naming:**
- Format: `YYYYMMDD_HHMMSS_XX_XXXX_3B_AnalyticMS_SR_file_format.tif`
- Example: `20251201_043244_37_250b_3B_AnalyticMS_SR_file_format.tif`
- Product type: 3B_AnalyticMS_SR (Surface Reflectance, multispectral)

**Metadata Files:**
- `*_metadata.json`: Scene properties (cloud cover, acquisition time, sensor parameters)
- `*.json`: STAC format with scene geometry

**Image Files Per Scene:**
- `*_3B_AnalyticMS_SR_file_format.tif`: 4-band surface reflectance (Blue, Green, Red, NIR)
- `*_3B_udm2_file_format.tif`: 8-band usable data mask (clear, snow, shadow, hazes, cloud, confidence, udm1)
- `*_3B_AnalyticMS_metadata.xml`: Detailed XML metadata

**Block Organization:**
- Scenes are grouped into geographic blocks based on spatial overlap/coverage
- Block assignments must be determined manually and hardcoded in mosaic script

## Development Notes

**Choosing the Right Selection Script:**
- Use `select_scenes_flood_aware.py` for flood assessment - it ensures scenes with water are not rejected due to high cloud cover
- Use `select_scenes_to_shp.py` for general purposes where only cloud cover matters

**Modifying Cloud Cover Thresholds:**
When adjusting cloud cover filtering, remember that internal metadata uses decimal format (0-1) while user-facing values use percentages (0-100).

**Water Detection Sensitivity:**
If water detection is too sensitive (detecting dark land as water) or not sensitive enough (missing actual water), adjust `--nir-threshold`:
- Increase threshold (e.g., 1500) to be more sensitive (more pixels classified as water)
- Decrease threshold (e.g., 800) to be more conservative (fewer pixels classified as water)
- Water typically has NIR reflectance < 10% (< 1000 in 0-10000 scale)

**Adding New Blocks:**
To add blocks to the mosaic script, follow the existing pattern:
```bash
mosaic_block N \
    "scene1_with_highest_cloud.tif" \
    "scene2_with_medium_cloud.tif" \
    "scene3_with_lowest_cloud.tif"
```

**Changing Mosaic Parameters:**
OTB mosaic parameters are set in the `mosaic_block()` function. Key parameters affecting output quality:
- `-comp.feather`: Controls edge blending (options: none, small, large)
- `-harmo.method`: Radiometric harmonization (options: none, band, rgb)
- `-interpolator`: Resampling method (options: nn, linear, bco)

**Path Configuration:**
Before running `mosaic_by_block.sh`, update these paths:
- `OTB_MOSAIC`: Location of OrfeoToolbox installation
- `INPUT_DIR`: Directory with input TIFF files
- `OUTPUT_DIR`: Destination for mosaics
