from subprocess import run
from loguru import logger
import xarray as xr
import numpy as np
import itertools
import argparse
import requests
import pathlib
import base64
import gdal
import tqdm
import json
import sys
import os

p = argparse.ArgumentParser()
p.add_argument('original_path')
p.add_argument('-o', '--overwrite', action='store_true', default=False)
args = p.parse_args()

original_path = pathlib.Path(args.original_path)

script_folder = pathlib.Path(__file__).parent.resolve()
snap_graph_folder = script_folder / 'snap_graphs'

tmp_folder = pathlib.Path('/tmp/polartep')
tmp_folder.mkdir(exist_ok=True)

def run_cmd(cmd):
    logger.debug(f'Running command: {cmd}')
    run(cmd, shell=True)

def make_snap_feature(graph_file, original_path, output_path, *extra_args):
    cmd = f'gpt {snap_graph_folder / graph_file} -PinFile={original_path} -PoutFile={output_path} ' + ' '.join(extra_args)
    run_cmd(cmd)

def create_features(original_path, tmp_folder):
    original_path = pathlib.Path(original_path).absolute()
    logger.debug(f'Creating features for product: {original_path}')

    make_snap_feature("HH_db.xml", original_path, tmp_folder / "HH_db.dim")
    make_snap_feature("HV_db.xml", original_path, tmp_folder / "HV_db.dim")
    make_snap_feature("IA.xml", original_path, tmp_folder / "IA.dim")

create_features(args.original_path, tmp_folder)


# Salman's implementation requires these exact values, so don't change them
BATCH_SIZE = 1000
PATCH_SIZE = 20
NUMBER_OF_BANDS = 3

HOPS_BASE_URL = 'https://hops.site/hopsworks-api/api'
MODEL_URL = HOPS_BASE_URL + '/project/22255/inference/models/seaIce1000:predict'
session = requests.Session()
session.headers.update({
    "Authorization": 'ApiKey tmHXmerVi7DsXu92.dxrJ8OGaj28eyPSelvKBgAee1nugoSP0umotTjjODQyJcdj3bTU1yvn4VRrzn2dp'
})


MODEL_CLASS_LABELS = {
    0: 'Water',
    1: 'Sea Ice',
}


HH = xr.open_rasterio('/tmp/polartep/HH_db.data/Sigma0_HH_db.img')[0]
HV = xr.open_rasterio('/tmp/polartep/HV_db.data/Sigma0_HV_db.img')[0]
IA = xr.open_rasterio('/tmp/polartep/IA.data/incAngle.img')[0]

def normalize(x, vmin, vmax):
    return (x - vmin) / (vmax - vmin)

def truncate(x, vmin, vmax):
    x[x < vmin] = vmin
    x[x > vmax] = vmax
    return x

rows, cols = HH.shape
X, Y = np.meshgrid(
    np.arange(0, rows-PATCH_SIZE, PATCH_SIZE), # TODO: Does not account for edges of image.
    np.arange(0, cols-PATCH_SIZE, PATCH_SIZE),
)

number_of_output_points = X.size
number_of_batches = number_of_output_points // BATCH_SIZE + 1

labels = np.zeros_like(HH, dtype=np.uint8)

all_points = zip(Y.flat, X.flat)

for batch_number in tqdm.tqdm(range(number_of_batches)):
    points_in_batch = list(itertools.islice(all_points, BATCH_SIZE))
    
    patches = list([
        np.dstack([
            normalize(HV[row:row+PATCH_SIZE, col:col+PATCH_SIZE].data, vmin=-35, vmax=-5),
            normalize(HH[row:row+PATCH_SIZE, col:col+PATCH_SIZE].data, vmin=-30, vmax=0),
            IA[row:row+PATCH_SIZE, col:col+PATCH_SIZE].data / 46
        ]) for (row, col) in points_in_batch
    ])
    patches.extend(np.zeros((PATCH_SIZE, PATCH_SIZE, NUMBER_OF_BANDS)) for _ in range(BATCH_SIZE - len(points_in_batch)))

    batch = np.stack([patches])
    encoded_batch = base64.b64encode(np.array(batch))
    response = session.post(
        MODEL_URL, 
        json = {
            'inputs': [
                {'b64': encoded_batch.decode('utf-8')}
            ]
        }
    )
    if not response.status_code == 200:
        logger.warning(f'Error running prediction for batch {batch_number}.')
        continue

    data = response.json()
    predicted_labels = data['outputs']['classes'][:len(points_in_batch)]

    for (row, col), label in zip(points_in_batch, predicted_labels):
        labels[row:row+PATCH_SIZE, col:col+PATCH_SIZE] = label

output_path = tmp_folder / str(original_path.stem + '.tif')

driver = gdal.GetDriverByName('GTIFF')
out = driver.Create(output_path, rows, cols, 1, gdal.GDT_Byte)
out.GetRasterBand(1).WriteArray(labels)
out.FlushCache()
