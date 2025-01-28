from __future__ import annotations

import os
import warnings
import time
import logging
from typing import TYPE_CHECKING, Tuple
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError
import requests

import rasterio as rst

from rasterio import MemoryFile
from shapely.geometry import Polygon, MultiPolygon
from pyogrio import read_dataframe
from owslib.wms import WebMapService

from .geom import *

if TYPE_CHECKING:
    import pandas

logger = logging.getLogger(__name__)


def send_request(
    url : str, 
    layer : str, 
    crs : str, 
    bounds : Tuple,
    width : Tuple,
    height : Tuple,
    backend : str = 'owslib',
    version : str = '1.3.0'
) -> np.ndarray:
    """
    Send a request through the specified `backend` to retrieve an image from a WMS server.

    Parameters:
        url (str): 
            HTTP(S) WMS address.
        layer (str): 
            Layer name to query.
        crs (str): 
            Coordinate/projection system name as e.g. "EPSG:4326".
        bounds (Tuple): 
            Extent to query.
        width (Tuple): 
            Output width of the image.
        height (Tuple): 
            Output height of the image.
        backend (str, optional): 
            Backend package to send the request through. One of:
                'urllib'
                'owslib'
            Defaults to 'owslib'.
        version (str, optional): 
            WMS version. Defaults to '1.3.0'.

    Returns:
        xr.DataArray: 
            Queried image as an array.
    """    
    match backend:
        case 'owslib':
            wms = WebMapService(url, version=version)
            request = wms.getmap(
                layers=[layer],
                srs=crs,
                format='image/png',
                bbox=bounds,
                size=(width, height)
            )
        case 'urllib':
            url_long = url + '&' + '&'.join([
                'request=GetMap',
                'service=WMS',
                f'version={version}',
                f'layers={layer}', 
                'format=image/png', 
                f'crs={crs}', 
                f'width={width}', 
                f'height={height}', 
                'bbox={},{},{},{}'.format(*bounds)
            ])
            request = urlopen(url_long).read()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with MemoryFile(request) as memfile:
            with memfile.open() as src:
                data = src.read()

    return data

def get_image(
    geom : Polygon | MultiPolygon, 
    url : str, 
    layer : str,
    crs : str,
    res : int | float,
    out_path : str | Path,
    max_len : int = 4000, 
    padding : Tuple | int = None,
    backend : str = 'owslib',
    tries : int = 3
) -> None:
    """
    Parse input geometries `geom` and send a request to download an image from the WMS server.
    If the input geometry exceeds the `max_len` it will be split and the output image will be
    built in chunks instead.

    Parameters:
        geom (Polygon | MultiPolygon): 
            Input geometry to calculate extent/bounding box from.
        url (str): 
            HTTP(S) WMS address.
        layer (str): 
            Layer name to query.
        crs (str): 
            Coordinate/projection system name.
        res (int | float): 
            Spatial resolution in georeferenced units.
        out_path (str | Path): 
            Full output path.
        max_len (int, optional): 
            Maximum axis length of a polygon, in pixels. If you experience persistent timeout
            errors try lowering this value. Defaults to 4000.
        padding (Tuple | int, optional): 
            Minimum distance to pad each axis with, in georeferenced units. If int, both axes are
            padded by the same amount. Defaults to None.
        backend (str, optional): 
            Backend package to send the request through. One of:
                'urllib'
                'owslib'
            Defaults to 'owslib'.
        tries (int, optional): 
            Number of tries to attempt to request an image from the server. Defaults to 3.

    Raises:
        RuntimeError: 
            Total number of tries have been exhausted on the server and no image could be retrieved.
    """

    bounds, width, height = get_dims(geom.bounds, res, padding=padding)
    gdf = split_geom(geom, crs, res, max_len=max_len)
    meta = {
        'driver' : 'GTiff',
        'dtype' : 'uint8',
        'nodata' : 0,
        'width' : width,
        'height' : height,
        'count' : 3,
        'crs' : crs,
        'transform' : rst.transform.from_bounds(*bounds, width, height)
    }
    
    with rst.open(out_path, 'w', **meta) as dst:
        for _, g in gdf.iterrows():
            b, w, h = dims = get_dims(g.geometry.bounds, res)
            for i in range(tries):
                try:
                    data = send_request(url, layer, crs, *dims, backend=backend)
                except (HTTPError, requests.exceptions.HTTPError) as err:
                    if backend=='owslib':
                        err_code = err.response.status_code
                    elif backend=='urllib':
                        err_code = err.code
                    if (err_code==504) & (i<tries-1):
                        print('Request timed out, retrying in 5 seconds.')
                        time.sleep(5)
                        continue
                else:
                    break
            else:
                raise RuntimeError('WMS request failed.')
            window = rst.windows.from_bounds(*b, transform=meta['transform'])
            dst.write(data, window=window)


def query_grid(
    grid : str, 
    index : str | int | float = None
) -> pandas.DataFrame:
    """
    Query one of the built-in grid systems to retrieve geometries.

    Parameters:
        grid (str): 
            Name of the grid system. One of:
                'dk',
        index (str | int | float, optional): 
            Index for geometry in the grid. If None, returns the full grid. Defaults to None.

    Returns:
        pandas.DataFrame: 
            Dataframe of geometries.
    """
    root = os.path.join(os.path.abspath(Path(os.path.dirname(__file__)).parents[0]), 'grid')

    match grid.lower():
        case 'dk1' | 'dk1km':
            df = read_dataframe(os.path.join(root, 'DKN_1km_euref89.zip')).set_index('KN1kmDK')
        case 'dk10' | 'dk10km':
            df = read_dataframe(os.path.join(root, 'DKN_10km_euref89.zip')).set_index('KN10kmDK')
    
    if index is not None:
        return df.loc[index]
    else:
        return df


def get_layer_name(
    service : str, 
    year : str | int, 
    res : int = 0.125, 
    season : str = 'spring', 
    bands : str = 'rgb'
) -> str:
    """
    Retrieve layer name of WMS service.

    Parameters:
        service (str): 
            Name of service. One of:
                'dk',
        year (str | int): 
            Year of imagery.
        res (int, optional): 
            Spatial resolution of imagery in georeferenced units. Defaults to 0.125.
        season (str, optional): 
            Season to query imagery for. This parameter is ignored if only one set of imagery 
            is available per year. Defaults to 'spring'.
        bands (str, optional): 
            Imagery band order. Either 'rgb' or 'cir', if available. Defaults to 'rgb'.

    Raises:
        ValueError: 
            Unimplemented service error.

    Returns:
        str: 
            WMS layer name.
    """    
    match service:
        case 'dk' | 'denmark':
            resstr = '10' if res==0.1 else '12_5'
            bands = '_cir' if bands=='cir' else ''
        case _:
            raise ValueError('Only the "dk" service has been implemented')

    layers = {
        'dk' : {
            'spring' : f'geodanmark_{str(year)}_{resstr}cm{bands}'
        }
    }
    
    return layers[service][season]