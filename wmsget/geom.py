from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Tuple

import numpy as np
import geopandas as gpd
from shapely.geometry import LineString, Polygon
from shapely.ops import split, polygonize

if TYPE_CHECKING:
    import pyproj


logger = logging.getLogger(__name__)


def split_geom(
    geometry : Polygon, 
    crs : pyproj.crs.crs.CRS,
    res : float,
    max_len : int = 4000,
    buffer : int = 0, **kwargs
) -> gpd.GeoDataFrame:
    """
    Splits a polygon geometry if a side (height or width) is longer than the max_len.
    The number of polygons created will be equal to <input_length>//`max_len`+1.

    Parameters:
        geometry (Polygon): 
            Input geometry.
        crs str | (pyproj.crs.crs.CRS): 
            Coordinate/projection system name.
        res (float): 
            Spatial resolution in georeferenced units.
        max_len (int, optional): 
            Maximum axis length of a polygon, in pixels. If you experience persistent timeout
            errors try lowering this value. Defaults to 4000.
        buffer (int, optional): 
            Geometry buffer size. Setting this value higher than 0 will result in overlap
            between sub-parts. Defaults to 0.

    Returns:
        gpd.GeoDataFrame: 
            Geodataframe with sub-part geometries.
    """    
    (minx, miny, maxx, maxy), width, height = get_dims(geometry.bounds, **kwargs)
    lines = []
    if width > max_len:
        xlines = np.linspace(minx, maxx, 1+int(np.ceil((maxx-minx) / res / max_len)))[1:-1]
        for xline in xlines:
            lines.append(LineString([(xline, miny), (xline, maxy)]))
    if height > max_len:
        ylines = np.linspace(miny, maxy, 1+int(np.ceil((maxy-miny) / res / max_len)))[1:-1]
        for yline in ylines:
            lines.append(LineString([(minx, yline), (maxx, yline)]))
    if len(lines)==0:
        return gpd.GeoDataFrame(geometry=[geometry])
    geoms = []
    for line in lines:
        geoms.extend([g for g in split(geometry, line).geoms])

    gdf = gpd.GeoDataFrame(geometry=list(polygonize(gpd.GeoSeries(geoms, crs=crs).exterior.union_all())))
    gdf = gdf[gdf.area>1]
    gdf = gdf[gdf.intersection(geometry).area>10]
    slivers = gdf[gdf.area<100]
    gdf = gdf[gdf.area>=100]

    for _, sliver in slivers.iterrows():
        nbs = gdf[gdf.touches(sliver.geometry)]
        if not nbs.empty:
            nb = nbs.iloc[0]
            gdf.loc[nb.name, 'geometry'] = nb.geometry.union(gpd.GeoSeries(sliver))[0]
    gdf.geometry = gdf.geometry.buffer(buffer, cap_style='square', join_style='mitre')
    gdf = gdf.reset_index(drop=True)
    return gdf


def get_dims(
    bounds : Tuple[float, float, float, float], 
    res : float = .125,
    padding : Tuple[int, int] = None,
    min_len : int = 256
) -> Tuple[Tuple[float, float, float, float], int, int]:
    """
    Retrieve the pixel width and height from a given set of bounds and optional buffer.
    If the output bounds are smaller than the `min_len`, the bounds will be padded to match
    the `min_len`.

    Parameters:
        bounds (Tuple[float, float, float, float]): 
            Input bounds as (minx, miny, maxx, maxy)
        res (float, optional): 
            Spatial resolution in georeferenced units. Defaults to .125.
        padding (Tuple[int, int] | int, optional): 
            Minimum distance to pad each axis with, in georeferenced units. If int, both axes are
            padded by the same amount. Defaults to None.
        min_len (int, optional): 
            Minimum length of an axis in pixels. Defaults to 256.

    Returns:
        Tuple[Tuple[float, float, float, float], int, int]: 
            Tuple of bounds, width, and height
    """    
    if padding is None:
        y_buffer, x_buffer = (0,0)
    elif isinstance(padding, int):
        y_buffer, x_buffer = (padding, padding)
    elif isinstance(padding, tuple):
        y_buffer, x_buffer = padding
        
    minx, miny, maxx, maxy = bounds
    minx -= x_buffer
    miny -= y_buffer
    maxx += x_buffer
    maxy += y_buffer
    width = int((maxx - minx) / res)
    height = int((maxy - miny) / res)
    if width < min_len:
        return get_dims(
            (minx, miny, maxx, maxy), 
            x_buffer=int(np.ceil(((min_len - width) / 2)*res)),
            y_buffer=0
        )
    elif height < min_len:
        return get_dims(
            (minx, miny, maxx, maxy), 
            x_buffer=0,
            y_buffer=int(np.ceil(((min_len - height) / 2)*res)),
        )
    return (minx, miny, maxx, maxy), width, height