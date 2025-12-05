#!/bin/bash
#
# Mosaic PlanetScope scenes by block attribute using OrfeoToolbox
# Images ordered by cloud cover (highest first = bottom, lowest last = top)
#
# Usage: ./mosaic_by_block.sh
#

# Configuration
OTB_MOSAIC="/Users/macbook/OTB-8.1.2-Darwin64/bin/otbcli_Mosaic"
INPUT_DIR="/Volumes/Extreme SSD/00_Sumatera/December 1/PlanetScope/PSScene"
OUTPUT_DIR="/Volumes/Extreme SSD/00_Sumatera/December 1/PlanetScope/PSScene/mosaic"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "PlanetScope Mosaic by Block"
echo "Images ordered by cloud cover (highest first)"
echo "=========================================="
echo "Input directory: $INPUT_DIR"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Function to mosaic a block
mosaic_block() {
    local block=$1
    shift
    local files=("$@")

    echo "Processing Block $block (${#files[@]} scenes)..."

    # Build input list - all files after single -il flag
    local input_files=""
    for f in "${files[@]}"; do
        input_files="$input_files \"$INPUT_DIR/$f\""
    done

    local output_file="$OUTPUT_DIR/mosaic_block_${block}.tif"

    # Run OTB Mosaic
    # Parameters: feather=large, harmo.method=band, harmo.cost=rmse, interpolator=nn
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
        echo "  -> ERROR creating mosaic for block $block"
    fi
    echo ""
}

# Block 1: 5 scenes (ordered by cloud cover: 43% -> 2%)
mosaic_block 1 \
    "20251201_043244_37_250b_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_043339_66_2535_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_043242_21_250b_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_042824_10_251f_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_043404_23_24de_3B_AnalyticMS_SR_file_format.tif"

# Block 2: 15 scenes (ordered by cloud cover: 46% -> 2%)
mosaic_block 2 \
    "20251201_043640_94_24ee_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_042643_84_2541_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_042502_44_2501_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_042504_59_2501_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_044051_58_24df_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_042636_88_2541_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_043915_46_24fd_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_042641_52_2541_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_042500_29_2501_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_043638_91_24ee_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_042639_20_2541_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_043636_89_24ee_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_044049_59_24df_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_042458_14_2501_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_043913_48_24fd_3B_AnalyticMS_SR_file_format.tif"

# Block 3: 4 scenes (ordered by cloud cover: 33% -> 10%)
mosaic_block 3 \
    "20251201_042648_48_2541_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_042650_80_2541_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_044059_52_24df_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_044101_51_24df_3B_AnalyticMS_SR_file_format.tif"

# Block 4: 4 scenes (ordered by cloud cover: 28% -> 0%)
mosaic_block 4 \
    "20251201_043624_33_24f3_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_043622_32_24f3_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_043620_31_24f3_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_043618_30_24f3_3B_AnalyticMS_SR_file_format.tif"

# Block 5: 3 scenes (ordered by cloud cover: 42% -> 28%)
mosaic_block 5 \
    "20251201_041917_42_253b_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041915_10_253b_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041912_79_253b_3B_AnalyticMS_SR_file_format.tif"

# Block 6: 2 scenes (ordered by cloud cover: 48% -> 43%)
mosaic_block 6 \
    "20251201_041627_53_24da_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041625_40_24da_3B_AnalyticMS_SR_file_format.tif"

# Block 7: 5 scenes (ordered by cloud cover: 48% -> 3%)
mosaic_block 7 \
    "20251201_041415_93_2507_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041324_82_251b_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041413_82_2507_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041411_71_2507_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041322_91_251b_3B_AnalyticMS_SR_file_format.tif"

# Block 8: 4 scenes (ordered by cloud cover: 36% -> 19%)
mosaic_block 8 \
    "20251201_041653_10_24da_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041657_36_24da_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041655_23_24da_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041659_49_24da_3B_AnalyticMS_SR_file_format.tif"

# Block 9: 7 scenes (ordered by cloud cover: 34% -> 0%)
mosaic_block 9 \
    "20251201_041113_62_2526_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_040859_82_253a_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_040857_54_253a_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041111_54_2526_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041001_61_253f_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041003_90_253f_3B_AnalyticMS_SR_file_format.tif" \
    "20251201_041408_84_251b_3B_AnalyticMS_SR_file_format.tif"

echo "=========================================="
echo "Mosaic complete!"
echo "Output files in: $OUTPUT_DIR"
ls -lh "$OUTPUT_DIR"/mosaic_block_*.tif 2>/dev/null || echo "No output files found"
echo "=========================================="
