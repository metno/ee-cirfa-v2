import tensorflow as tf
from rasterio import windows
from itertools import product
import rasterio as rio
import os
import numpy as np
import matplotlib.pyplot as plt
import tqdm
import math
import base64
import json
import requests as c
from os import listdir
from os.path import isfile, join


patch_size = 20
batch_size = 1000
ice = np.ones((patch_size,patch_size,3),dtype='float32')
ice[:,:] = [255,255,0]
sea = np.zeros((patch_size,patch_size,3),dtype='float32')
sea[:,:] = [0,0,255]

# You should update the AuthorizationToken 
AuthorizationToken = "Bearer eyJraWQiOiI2IiwidHlwIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJhdWQiOiJhcGkiLCJzdWIiOiJzYWxtYW5raCIsIm5iZiI6MTU3NTk5MjAzNiwicmVuZXdhYmxlIjp0cnVlLCJleHBMZWV3YXkiOjkwMCwicm9sZXMiOlsiSE9QU19VU0VSIl0sImlzcyI6ImhvcHN3b3Jrc0Bsb2dpY2FsY2xvY2tzLmNvbSIsImV4cCI6MTU3NTk5MzgzNiwiaWF0IjoxNTc1OTkyMDM2LCJqdGkiOiIzOGEzYmU4My0yOWZjLTRlMWYtOTNlOS00ODkzODllOGY4ZTIifQ.U8XnIXfqVuQqX2wsYSP5rz2IzLjnqOishxzVwtwJI_HgCIAPQQ5G78TjX2FcNl-c3HzYzNnR4Go2nqbvYiUeRg"



def get_tiles(ds, width=patch_size, height=patch_size):
    nols, nrows = ds.meta['width'], ds.meta['height']
    offsets = product(range(0, nols, width), range(0, nrows, height))
    big_window = windows.Window(col_off=0, row_off=0, width=nols, height=nrows)
    for col_off, row_off in offsets:
        if col_off == 1:
            print('yes')
        window = windows.Window(col_off=col_off, row_off=row_off, width=width, height=height).intersection(
            big_window)
        transform = windows.transform(window, ds.transform)
        yield window, transform
input = []
im_dir = '.'
ia_dir = '.'
for f in listdir(im_dir):
    if isfile(join(im_dir, f)) and f.endswith("scaled.tif"):
        t = (join(im_dir, f), join(ia_dir, '_'.join(f.split('_')[0:9]) + '_IA.tif'))
        input.append(t)
times = []
for file in tqdm.tqdm(input):
    input_filename = file[0]
    ia_image = file[1]
    seg_img = []
    in_path = './'
    out_path = '.'
    import time
    output_filename = 'tile_{}-{}.tif'
    test_patches = []
    start1 = time.time()
    patch_size = 20

    with rio.open(os.path.join(in_path, input_filename)) as inds:
        tile_width, tile_height = patch_size, patch_size
        meta = inds.meta.copy()
        ia = rio.open(ia_image)
        for window, transform in tqdm.tqdm(get_tiles(inds)):
            #         print(window)
            meta['transform'] = transform
            meta['width'], meta['height'] = window.width, window.height
            outpath = os.path.join(out_path, output_filename.format(int(window.col_off), int(window.row_off)))
            t = inds.read(window=window) / 255
            tt = ia.read(1, window=window) / 46
            t[2, :, :] = tt
            p = t

            if p.shape[1] != patch_size:
                t1 = np.pad(p[0], ((patch_size - p.shape[1], 0), (0, 0)), 'constant')
                t2 = np.pad(p[1], ((patch_size - p.shape[1], 0), (0, 0)), 'constant')
                t3 = np.pad(p[2], ((patch_size - p.shape[1], 0), (0, 0)), 'constant')
                tt = np.dstack((t1, t2, t3)).reshape(3, patch_size, p.shape[2])
                p = tt
            if p.shape[2] != patch_size:
                t1 = np.pad(p[0], ((0, 0), (patch_size - p.shape[2], 0)), 'constant')
                t2 = np.pad(p[1], ((0, 0), (patch_size - p.shape[2], 0)), 'constant')
                t3 = np.pad(p[2], ((0, 0), (patch_size - p.shape[2], 0)), 'constant')
                tt = np.dstack((t1, t2, t3)).reshape(3, p.shape[1], patch_size)
                p = tt
            # test_patches.append(inds.read(1, window=window))
            test_patches.append(np.rollaxis(p, 0, 3))
            if test_patches.__len__() == batch_size:
                encoded_input_string = base64.b64encode(np.array(test_patches, 'float32'))
                input_string = encoded_input_string.decode("utf-8")
                instance = [{"b64": input_string}]
                f = json.dumps({"inputs": instance})
                headers = {"content-type": "application/json",
                           "Authorization": AuthorizationToken}
                s = time.time()
                resp = c.post(
                    'https://www.hops.site:443/hopsworks-api/api/project/22255/inference/models/seaIce1000:predict',
                    data=f, headers=headers)
                print(time.time()-s)
                if resp.status_code == 200:
                    # print(resp.status_code)
                    r = resp.json()
                    for p in r['outputs']['classes']:
                        if p == 1:
                            seg_img.append(ice)
                        else:
                            seg_img.append(sea)
                    test_patches = []
                else:
                    print("Web Service Error: {}".format(resp.status_code))
                    exit()
    print(inds.height, inds.width, inds.transform, inds.crs)
    imgs_comb = []
    s_image = []
    j = 0
    i = 0
    src = rio.open(input_filename)
    image = src.read()
    image = np.rollaxis(image, 0, 3)
    num_hight = math.ceil(src.height / patch_size)
    num_width = math.ceil(src.width / patch_size)
    for i in range(0, num_width - 1):
        imgs_comb.append(np.vstack(seg_img[j:j + num_hight]))
        j += num_hight
    s_image = np.hstack(imgs_comb)
    plt.subplots(1, 2, figsize=(15, 15))
    plt.subplot(1, 2, 1)
    plt.imshow(s_image)
    plt.subplot(1, 2, 2)
    plt.imshow(image)
    plt.savefig(input_filename.split('\\')[1] + '_20x20_SeaIceClassification_rest.jpg', dpi=1000)

