from loguru import logger
import argparse
import pathlib
import sys

import classifier
import shell
import snap

FEATURE_FOLDER = pathlib.Path('/tmp/polartep')

p = argparse.ArgumentParser()
p.add_argument('original_path')
p.add_argument('-epsg', '--epsg-code', type=int, default=3575)
p.add_argument('-ps', '--pixel-spacing', type=int, default=200)
args = p.parse_args()

original_path = pathlib.Path(args.original_path)
if original_path.name == 'manifest.safe':
    product_id = original_path.parent.stem
elif original_path.name.endswith('.zip'):
    product_id = original_path.stem
else:
    logger.error('Unknown naming convention')
    sys.exit(1)

if args.pixel_spacing < 40:
    logger.error(f'Pixel spacing must be larger than 40 meters. Input arguments: {args}')
    sys.exit(1)

# Create features using the ESA SNAP Sentinel-1 Toolbox
# Calibrates the data and produces a set of feature images
# with a specific naming convention into a `FEATURE_FOLDER`
snap.create_features(args.original_path, FEATURE_FOLDER)

# Classify image using Tensorflow model
# Produces an ENVI product `FEATURE_FOLDER/labels.{img,hdr}`, which contains the
# predicted class labels.
classifier.classify(FEATURE_FOLDER)

# Merge class label image with original images to put metadata back
# Produces a new SNAP-compatible dataset `features/folder/merged.{dim,data}`
snap.put_metadata_back(FEATURE_FOLDER)

tif_output_path = f'/workdir/{product_id}_classified.tif'
logger.debug(f'Writing results to {tif_output_path}')
# Geocoded result using SNAP
shell.run_cmd(f'gpt Ellipsoid-Correction-RD -PmapProjection=EPSG:{args.epsg_code} -PalignToStandardGrid=true -PpixelSpacingInMeter={args.pixel_spacing} -f GeoTIFF -t {tif_output_path} merged.dim', workdir=FEATURE_FOLDER)

# 8 bit for map view
f8bit_output_path = f'/workdir/{product_id}_8bit.tif'
shell.run_cmd(f'gpt Convert-Datatype -PtargetDataType=uint8 -PtargetScalingStr="Linear (between 95% clipped histogram)" -PtargetNoDataValue=0.0 -f GeoTIFF -t {f8bit_output_path} {tif_output_path}', workdir=FEATURE_FOLDER)

# Zip result
zip_output_path = f'/workdir/{product_id}_results.zip'
#logger.debug(f'Writing results to {output_path}')
shell.run_cmd(f'zip -r -0 {zip_output_path} {tif_output_path} {f8bit_output_path}', workdir=FEATURE_FOLDER)
