#!/bin/bash
#
# Auto-generated mosaic script for aceh1
# Scenes filtered by GeoJSON boundary and clustered spatially
#

# Configuration
OTB_MOSAIC="/Users/macbook/OTB-8.1.2-Darwin64/bin/otbcli_Mosaic"
INPUT_DIR=".."
OUTPUT_DIR="../mosaic_aceh1"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "PlanetScope Mosaic - aceh1"
echo "Scenes ordered by cloud cover (highest first = bottom)"
echo "=========================================="
echo "Input directory: $INPUT_DIR"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Function to mosaic a cluster
mosaic_cluster() {
    local cluster=$1
    shift
    local files=("$@")

    echo "Processing Cluster $cluster (${#files[@]} scenes)..."

    # Build input list
    local input_files=""
    for f in "${files[@]}"; do
        input_files="$input_files \"$INPUT_DIR/$f\""
    done

    local output_file="$OUTPUT_DIR/mosaic_${cluster}.tif"

    # Run OTB Mosaic
    eval "$OTB_MOSAIC" \
        -il $input_files \
        -out "\"$output_file\"" uint16 \
        -comp.feather large \
        -harmo.method band \
        -harmo.cost rmse \
        -interpolator nn \
        -nodata 0 \
        2>&1 | grep -v "^WARN"

    if [ -f "$output_file" ]; then
        echo "  -> Created: $output_file"
    else
        echo "  -> ERROR creating mosaic for cluster $cluster"
    fi
    echo ""
}

# cluster_1: 14 scenes (cloud cover: 33% -> 0%)
mosaic_cluster cluster_1 \
    "20251201_042648_48_2541_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_042650_80_2541_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_044059_52_24df_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_044101_51_24df_3B_AnalyticMS_SR_file_format.tif" \
    "20251129_042937_79_2547_3B_AnalyticMS_SR_file_format.tif" \
    "20251129_042933_20_2547_3B_AnalyticMS_SR_file_format.tif" \
    "20251129_042633_82_251e_3B_AnalyticMS_SR_file_format.tif" \
    "20251129_042935_49_2547_3B_AnalyticMS_SR_file_format.tif" \
    "20251129_042636_14_251e_3B_AnalyticMS_SR_file_format.tif" \
    "20251129_042801_83_2527_3B_AnalyticMS_SR_file_format.tif" \
    "20251129_042804_12_2527_3B_AnalyticMS_SR_file_format.tif" \
    "20251129_042631_51_251e_3B_AnalyticMS_SR_file_format.tif" \
    "20251129_042806_42_2527_3B_AnalyticMS_SR_file_format.tif" \
    "20251129_042808_71_2527_3B_AnalyticMS_SR_file_format.tif"

echo "=========================================="
echo "Mosaic complete!"
echo "Output files in: $OUTPUT_DIR"
ls -lh "$OUTPUT_DIR"/mosaic_*.tif 2>/dev/null || echo "No output files found"
echo "=========================================="
