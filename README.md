# PlanetScope Flood Monitoring - Mosaic Processing Workflow

Quick Response - Remote Sensing: A toolkit for processing PlanetScope satellite imagery for flood assessment in Quick Response operations, with automated scene selection, GeoJSON-based filtering, and hierarchical mosaicking.

## Overview

This repository implements a comprehensive workflow for processing PlanetScope 3B_AnalyticMS_SR (Surface Reflectance) imagery to create seamless mosaics for flood monitoring in Sumatra, Indonesia. Key features include:

- **Flood-aware scene selection**: NIR-based water detection to accept high-cloud scenes with visible water
- **Automatic spatial clustering**: DBSCAN-based grouping of nearby scenes
- **GeoJSON boundary filtering**: Select scenes within specific areas of interest
- **Hierarchical mosaicking**: Subdivide large areas for better radiometric harmonization
- **Band harmonization**: RMSE-based correction for consistent radiometry across satellites

## Directory Structure

```
.
├── scripts/                              # Python processing scripts
│   ├── select_scenes_flood_aware.py      # Flood-aware scene selection
│   ├── select_scenes_to_shp.py           # Convert scene list to shapefile
│   ├── cluster_and_mosaic.py             # Spatial clustering
│   └── mosaic_by_geojson.py              # GeoJSON-based mosaic generation
├── blocks/                               # GeoJSON boundaries for AOIs
│   ├── sumbar*.geojson                   # West Sumatra regions
│   ├── sumut*.geojson                    # North Sumatra regions
│   └── aceh*.geojson                     # Aceh regions
└── README.md                             # This file
```

## Requirements

### Software
- **Python 3.x** with packages:
  - `geopandas`, `shapely`, `rasterio`, `numpy`
  - `scikit-learn` (for DBSCAN clustering)
  - `pyshp` (for shapefile generation)
- **OrfeoToolbox (OTB) 8.1+** for mosaicking
- **GDAL 3.x** for pre-event data and VRT operations

### Data
- PlanetScope 3B_AnalyticMS_SR imagery (4-band: Blue, Green, Red, NIR)
- PlanetScope UDM2 masks for cloud/water detection
- GeoJSON boundaries defining areas of interest
- Optional: Pre-event baseline imagery

## Core Workflow

### 1. Scene Selection with Flood-Aware Filtering

**RECOMMENDED FOR FLOOD ASSESSMENT**: Uses NIR-based water detection to avoid rejecting high-cloud scenes that contain flood areas.

```bash
python3 scripts/select_scenes_flood_aware.py \
    --input-dir /path/to/planetscope/scenes \
    --output PSScene_flood_aware \
    --cloud-max 80 \
    --nir-threshold 1000 \
    --min-water-pct 1.0
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

**Output:**
- Shapefile with scene footprints and attributes: scene_id, cloud_cov, water_pct, selection reason
- Referenced TIFF files: `{scene_id}_3B_AnalyticMS_SR_file_format.tif`

### 2. Generate Mosaics by GeoJSON Boundary

Create mosaics for specific areas defined by GeoJSON boundaries:

```bash
python3 scripts/mosaic_by_geojson.py \
    --shapefile PSScene/PSScene_flood_aware.shp \
    --geojson blocks/aceh1.geojson \
    --data-dir /path/to/parent/directory \
    --output-script PSScene/mosaic_aceh1.sh
```

**Processing Steps:**
1. Filters scenes intersecting the GeoJSON boundary
2. Clusters nearby scenes using DBSCAN (eps_factor=1.5, min_samples=2)
3. Generates bash script with OTB mosaic commands
4. Applies band harmonization and edge feathering

**OTB Mosaic Parameters:**
- `-comp.feather large`: Edge blending for seamless transitions
- `-harmo.method band -harmo.cost rmse`: Per-band radiometric harmonization
- `-interpolator nn`: Nearest neighbor resampling (preserves original values)
- `-nodata 0`: No-data value for masking

### 3. Run the Generated Mosaic Script

```bash
cd PSScene/
./mosaic_aceh1.sh
```

**Output:** Mosaic saved to `mosaic_<aoi>/mosaic_cluster_1.tif`

### 4. Hierarchical Mosaicking (For Large Areas)

When mosaicking many scenes from different satellites shows excessive radiometric variation (gains <0.3 or >3.0):

**Step 1: Subdivide the AOI**

Create sub-boundaries (e.g., `aceh1a.geojson`, `aceh1b.geojson`) to split the area by satellite groups.

**Step 2: Mosaic each subdivision**

```bash
# Generate script for subdivision
python3 scripts/mosaic_by_geojson.py \
    --shapefile PSScene/PSScene_flood_aware.shp \
    --geojson blocks/aceh1a.geojson \
    --data-dir .. \
    --output-script PSScene/mosaic_aceh1a.sh

# Manually edit mosaic_aceh1a.sh to include only specific scenes
# (Remove unwanted scenes from the auto-generated list)

# Run mosaic
./mosaic_aceh1a.sh
```

**Step 3: Combine sub-mosaics**

```bash
#!/bin/bash
OTB_MOSAIC="/path/to/otbcli_Mosaic"

$OTB_MOSAIC \
    -il mosaic_aceh1a/mosaic_cluster_1.tif \
        mosaic_aceh1b/mosaic_cluster_1.tif \
    -out mosaic_aceh1_combined/mosaic_aceh1.tif uint16 \
    -comp.feather large \
    -harmo.method band \
    -harmo.cost rmse \
    -interpolator nn \
    -nodata 0
```

**Example Results:**
- aceh1 direct (14 scenes, 5 satellites): Harmonization gains 0.27-18.44 (poor)
- aceh1 hierarchical (8+6 scenes): Final gains 0.35-1.47 (excellent)

### 5. Pre-Event Baseline Mosaics

For pre-event mosaics using tiled basemap data:

```bash
#!/bin/bash
GEOJSON="blocks/aceh1.geojson"
INPUT_DIR="/path/to/pre-event/tiles"
OUTPUT_DIR="mosaic_aceh1_pre-event"

# Create VRT from all tiles
gdalbuildvrt "$OUTPUT_DIR/tiles.vrt" "$INPUT_DIR"/*.tif

# Crop to AOI boundary
gdalwarp \
    -cutline "$GEOJSON" \
    -crop_to_cutline \
    -co COMPRESS=LZW \
    -co PREDICTOR=2 \
    -co TILED=YES \
    -r bilinear \
    -multi \
    "$OUTPUT_DIR/tiles.vrt" \
    "$OUTPUT_DIR/mosaic_pre-event.tif"
```

## Completed AOI Mosaics

### West Sumatra (Sumbar)
- **sumbar1a**: 6 scenes → 1.7 GB
- **sumbar1b**: 2 scenes → 1.4 GB
- **sumbar1c**: 2 scenes → 1.4 GB
- **sumbar2**: 6 scenes → 2.6 GB

### North Sumatra (Sumut)
- **sumut1**: 4 scenes → 2.5 GB
- **sumut2**: 5 scenes → 2.8 GB
- **sumut3**: 2 scenes → 1.4 GB

### Aceh
- **aceh1_combined**: 14 scenes (8+6 hierarchical) → 6.0 GB
  - aceh1a: 8 scenes (251e, 2547, 24df satellites)
  - aceh1b: 6 scenes (2527, 2541 satellites)

**Total**: 41 scenes processed across 8 mosaics, 19.8 GB output

## Quick Start: Creating a New Mosaic

1. **Create GeoJSON boundary**
   - Use QGIS or geojson.io to define your area
   - Save as `blocks/my_aoi.geojson`

2. **Generate mosaic script**
   ```bash
   python3 scripts/mosaic_by_geojson.py \
       --shapefile PSScene/PSScene_flood_aware.shp \
       --geojson blocks/my_aoi.geojson \
       --data-dir /path/to/data \
       --output-script PSScene/mosaic_my_aoi.sh
   ```

3. **Review selected scenes**
   ```bash
   grep "3B_AnalyticMS_SR" PSScene/mosaic_my_aoi.sh
   ```

4. **(Optional) Edit scene list**

   If automatic selection includes too many/incompatible scenes:
   ```bash
   # Edit the script to keep only desired scenes
   nano PSScene/mosaic_my_aoi.sh
   ```

5. **Run mosaic**
   ```bash
   cd PSScene/
   ./mosaic_my_aoi.sh
   ```

6. **Verify output**
   ```bash
   ls -lh mosaic_my_aoi/mosaic_cluster_1.tif
   gdalinfo mosaic_my_aoi/mosaic_cluster_1.tif
   ```

## Troubleshooting

### Poor Radiometric Harmonization

**Symptom**: Visible seams between scenes, harmonization gains ranging from 0.2 to 18+

**Diagnosis**: Check OTB log for gain values in harmonization output:
```
[ Band 0 ]
Gains  : 0.27 18.44 ...  # BAD - extreme variation
Gains  : 0.95 1.05 ...   # GOOD - consistent
```

**Solution**: Use hierarchical mosaicking
1. Subdivide AOI by satellite groups or geography
2. Mosaic each group separately
3. Combine sub-mosaics

### Missing Scene Files

**Symptom**: Script references scenes that don't exist

**Solution**:
1. Check shapefile was created from existing TIFFs
2. Verify file paths in generated script
3. Manually remove non-existent scenes from script

### Memory Issues

**Symptom**: Processing hangs or crashes with large mosaics

**Solution**:
```bash
# Increase OTB RAM limit
export OTB_MAX_RAM_HINT=4096

# Or process in smaller chunks using hierarchical approach
```

### Water Detection Too Sensitive/Conservative

**Symptom**: Dark land classified as water, or floods not detected

**Solution**: Adjust NIR threshold
```bash
# More sensitive (detect more water)
--nir-threshold 1500

# More conservative (detect less water)
--nir-threshold 800
```

Water typically has NIR reflectance < 10% (< 1000 in 0-10000 scale)

## Data Specifications

### PlanetScope File Naming
- Format: `YYYYMMDD_HHMMSS_XX_XXXX_3B_AnalyticMS_SR_file_format.tif`
- Example: `20251201_043244_37_250b_3B_AnalyticMS_SR_file_format.tif`

### Band Structure
**AnalyticMS_SR** (UInt16, Surface Reflectance 0-10000):
- Band 1: Blue
- Band 2: Green
- Band 3: Red
- Band 4: NIR (used for water detection)

**UDM2** (Byte, 0=false/1=true masks):
- Band 1: clear
- Band 6: cloud
- Other: snow, shadow, haze_light, haze_heavy, confidence, udm1

### Harmonization Quality Indicators
- **Excellent**: Gains 0.8-1.2 across all scenes
- **Good**: Gains 0.5-2.0 across all scenes
- **Problematic**: Gains <0.3 or >3.0 indicate incompatible scenes

## Technical Notes

### Scene Selection Strategy
1. **Low cloud (<20%)**: Accept all scenes
2. **Medium cloud (20-50%)**: Accept if water visible
3. **High cloud (>50%)**: Reject unless significant water detected
4. **Flood events**: Prioritize water detection over cloud cover

### DBSCAN Clustering Parameters
- **eps_factor**: 1.5× average scene size (determines cluster radius)
- **min_samples**: 2 (minimum scenes to form a cluster)
- Ensures nearby scenes are mosaicked together

### OTB Processing Notes
- Default RAM limit: 256 MB (increase for large mosaics)
- Uses multi-threading (8 threads on this system)
- Temporary files created during processing are auto-cleaned
- Output format: GeoTIFF with uint16 data type

## Alternative Workflows

### Simple Cloud Cover Filtering (Non-Flood)

For general purposes where water detection is not needed:

```bash
python3 scripts/select_scenes_to_shp.py \
    --input-dir . \
    --cloud-max 50 \
    --output PSScene_selected
```

### Manual Block-Based Mosaicking

Legacy approach for hardcoded geographic blocks:

```bash
# Edit mosaic_by_block.sh to define blocks
./mosaic_by_block.sh
```

## References

- OrfeoToolbox Documentation: https://www.orfeo-toolbox.org/
- PlanetScope Product Specifications: https://www.planet.com/products/
- GDAL/OGR Documentation: https://gdal.org/
- DBSCAN Clustering: https://scikit-learn.org/stable/modules/clustering.html#dbscan

## License

[Your license information]

## Contact

For questions or issues regarding this workflow, please contact [your contact information]

---

**Last Updated**: December 2025
**Version**: 2.0
