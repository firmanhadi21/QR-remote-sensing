#!/bin/bash
#
# Combine aceh1a and aceh1b mosaics into final aceh1 mosaic
#

# Configuration
OTB_MOSAIC="/Users/macbook/OTB-8.1.2-Darwin64/bin/otbcli_Mosaic"
INPUT_DIR=".."
OUTPUT_DIR="../mosaic_aceh1_combined"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo "Combining aceh1a and aceh1b mosaics"
echo "=========================================="
echo "Input files:"
echo "  - mosaic_aceh1a/mosaic_cluster_1.tif (8 scenes)"
echo "  - mosaic_aceh1b/mosaic_cluster_1.tif (6 scenes)"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Mosaic the two outputs
echo "Processing combined mosaic..."

"$OTB_MOSAIC" \
    -il "$INPUT_DIR/mosaic_aceh1a/mosaic_cluster_1.tif" \
        "$INPUT_DIR/mosaic_aceh1b/mosaic_cluster_1.tif" \
    -out "$OUTPUT_DIR/mosaic_aceh1.tif" uint16 \
    -comp.feather large \
    -harmo.method band \
    -harmo.cost rmse \
    -interpolator nn \
    -nodata 0 \
    2>&1 | grep -v "^WARN"

if [ -f "$OUTPUT_DIR/mosaic_aceh1.tif" ]; then
    echo ""
    echo "  -> Created: $OUTPUT_DIR/mosaic_aceh1.tif"
else
    echo ""
    echo "  -> ERROR creating combined mosaic"
fi

echo ""
echo "=========================================="
echo "Combined mosaic complete!"
echo "Output file:"
ls -lh "$OUTPUT_DIR"/mosaic_aceh1.tif 2>/dev/null || echo "No output file found"
echo "=========================================="
