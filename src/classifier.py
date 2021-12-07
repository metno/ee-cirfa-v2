import tensorflow as tf
import xarray as xr
import numpy as np
import itertools
import requests
import pathlib
import gdal
import tqdm
import json
import sys
import os


MODEL_PATH = pathlib.Path(os.environ['MODEL_FOLDER'])

# The implementation requires these exact values, so don't change them
BATCH_SIZE = 1000
PATCH_SIZE = 20
NUMBER_OF_BANDS = 3

MODEL_CLASS_LABELS = {
    0: 'Water',
    1: 'Sea Ice',
}

OUTPUT_CLASS_LABELS = {
    'No data': 0,
    'Water': 1,
    'Sea Ice': 2,
    'Land': 3,
}

def normalize(x, vmin, vmax):
    return (x - vmin) / (vmax - vmin)

def truncate(x, vmin, vmax):
    x[x < vmin] = vmin
    x[x > vmax] = vmax
    return x

def classify(feature_folder):
    feature_folder = pathlib.Path(feature_folder)
    feature_folder.mkdir(exist_ok=True)

    model = tf.saved_model.load(MODEL_PATH.as_posix())
    infer = model.signatures["serving_default"]

    HH = xr.open_rasterio(feature_folder / 'HH_db.data' / 'Sigma0_HH_db.img')[0]
    HV = xr.open_rasterio(feature_folder / 'HV_db.data' / 'Sigma0_HV_db.img')[0]
    IA = xr.open_rasterio(feature_folder / 'IA.data' / 'incAngle.img')[0]
    landmask = xr.open_rasterio(feature_folder / 'landmask.data' / 'land.img')[0]


    rows, cols = HH.shape
    X, Y = np.meshgrid(
        np.arange(0, cols-PATCH_SIZE, PATCH_SIZE),
        np.arange(0, rows-PATCH_SIZE, PATCH_SIZE),
    )

    number_of_output_points = X.size
    number_of_batches = number_of_output_points // BATCH_SIZE + 1

    labels = np.zeros_like(HH, dtype=np.uint8)

    all_points = zip(Y.flat, X.flat)

    for batch_number in tqdm.tqdm(range(number_of_batches)):
        points_in_batch = list(itertools.islice(all_points, BATCH_SIZE))
        
        # Pre-process a batch of patches according to what the model expects
        patches = list([
            np.dstack([
                normalize(HH[row:row+PATCH_SIZE, col:col+PATCH_SIZE].data, vmin=-30, vmax=0),
                normalize(HV[row:row+PATCH_SIZE, col:col+PATCH_SIZE].data, vmin=-35, vmax=-5),
                IA[row:row+PATCH_SIZE, col:col+PATCH_SIZE].data / 46
            ]) for (row, col) in points_in_batch
        ])

        # Pad array so that it has exactly BATCH_SIZE number of patches, otherwise the inference step won't work
        patches.extend(np.zeros((PATCH_SIZE, PATCH_SIZE, NUMBER_OF_BANDS), dtype=np.float32) for _ in range(BATCH_SIZE - len(points_in_batch)))

        batch = np.array(patches)
        result = infer(tf.constant(batch))
        predicted_labels = result['classes'].numpy()

        for (row, col), label in zip(points_in_batch, predicted_labels):
            labels[row:row+PATCH_SIZE, col:col+PATCH_SIZE] = OUTPUT_CLASS_LABELS[MODEL_CLASS_LABELS[label]]

    labels[landmask == 0] = OUTPUT_CLASS_LABELS['Land']
    output_path = feature_folder / 'labels.img'

    driver = gdal.GetDriverByName('ENVI')
    out = driver.Create(output_path.as_posix(), cols, rows, 1, gdal.GDT_Byte)
    band = out.GetRasterBand(1)
    band.SetDescription('class_labels')
    band.SetNoDataValue(0)
    band.WriteArray(labels)
    out.FlushCache()
    del out
