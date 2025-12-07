#!/bin/bash
#
# Auto-generated mosaic script for sumut1
# Scenes filtered by GeoJSON boundary and clustered spatially
#

# Configuration
OTB_MOSAIC="/Users/macbook/OTB-8.1.2-Darwin64/bin/otbcli_Mosaic"
INPUT_DIR=".."
OUTPUT_DIR="../mosaic_sumut1"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "PlanetScope Mosaic - sumut1"
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

# cluster_1: 4 scenes (cloud cover: 36% -> 19%)
mosaic_cluster cluster_1 \
    "20251201_041653_10_24da_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041657_36_24da_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041655_23_24da_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041659_49_24da_3B_AnalyticMS_SR_file_format.tif"

echo "=========================================="
echo "Mosaic complete!"
echo "Output files in: $OUTPUT_DIR"
ls -lh "$OUTPUT_DIR"/mosaic_*.tif 2>/dev/null || echo "No output files found"
echo "=========================================="
