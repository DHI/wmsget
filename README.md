# wmsget
Python library for converting WMS images into geotiffs


# Installation
## As a package with pip
* Run Anaconda/Miniconda and activate your environment or create a new one
* Install git and pip

`conda install git pip`

* Install wmsget with pip

`pip install git+https://github.com/DHI/wmsget.git`

## Cloning the repository
* Clone the repository to a local path using git

`git clone https://github.com/DHI/wmsget.git`
 
* Install the package in your environment

`pip install "path/to/wmsget"`

&nbsp;

# Documentation
The package has one purpose so it only has one primary function with a few additional supporting features.

## Downloading an image
[**wmsget.get_image**(*geom, url, layer, crs, res, out_path, max_len=4000, padding=None, backend='owslib', tries=3*)](https://github.com/DHI/wmsget/blob/f672e0be95a4ee467deec6ea9d42be56b7f8680b/wmsget/wms.py#L98)

Gets the bounding box of the input geometry, parses the required parameters and sends a request to the specified WMS server to retrieve an image. For large images it will query in chunks. 

Parameters:
* **geom** (*[shapely.Polygon] | [shapely.MultiPolygon]*): Input geometry to calculate extent/bounding box from.
* **url** (*str*): HTTP(S) WMS address.
* **layer** (*str*): Layer name to query.
* **crs** (*str*): Coordinate/projection system name.
* **res** (*int | float*): Spatial resolution in georeferenced units.
* **out_path** (*str | Path*): Full output path.
* **max_len** (*int, optional*): Maximum axis length of a polygon, in pixels. If you experience persistent timeout errors try lowering this value. Defaults to 4000.
* **padding** (*Tuple | int, optional*): Minimum distance to pad each axis with, in georeferenced units. If int, both axes are padded by the same amount. Defaults to None.
* **backend** (*str, optional*): The backend package used to send the WMS request. One of:
    * **'owslib'** (*default*)
    * **'urllib'**
* **tries** (*int, optional*): 
    Number of tries to attempt to request an image from the server. Defaults to 3.


## Support functions
Additional support functions may be used to retrieve the grid geometries and layer names for support WMS services.

Support services as of yet:
* Dataforsyningen, orthophotos: `dk`

***

[**wmsget.query_grid**(*grid, index=None*)](https://github.com/DHI/wmsget/blob/f672e0be95a4ee467deec6ea9d42be56b7f8680b/wmsget/wms.py#L183)
Query one of the supported grid systems to retrieve geometries. 

Parameters:
* **grid** (*str*): Name of the grid system. One of:
    * **'dk1'**
    * **'dk10'**
* **index** (*str | int | float, optional*): Index for geometry in the grid. If None, returns the full grid. Defaults to None.

Returns:
* Dataframe of grid geometries

Return type:
* [pandas.DataFrame] 

***

[**wmsget.get_layer_name**(*service, year, res=0.125, season='spring', bands='rgb'*)](https://github.com/DHI/wmsget/blob/f672e0be95a4ee467deec6ea9d42be56b7f8680b/wmsget/wms.py#L214)

Retrieve the layer name of a WMS service.

Parameters:
* **service** (*str*): Name of service. One of:
    * **'dk'**,
* **year** (*str | int*): Year of imagery.
* **res** (*int, optional*): Spatial resolution of imagery in georeferenced units. Defaults to 0.125.
* **season** (*str, optional*): Season to query imagery for. This parameter is ignored if only one set of imagery is available per year. Defaults to 'spring'.
* **bands** (*str, optional*): Imagery band order. Either 'rgb' or 'cir', if available. Defaults to 'rgb'.

Returns:
* WMS layer name.

Return type:
* str


[//]: # (External references)
[shapely.Polygon]: https://shapely.readthedocs.io/en/2.0.6/reference/shapely.Polygon.html "shapely Polygon documentation"
[shapely.MultiPolygon]: https://shapely.readthedocs.io/en/2.0.6/reference/shapely.MultiPolygon.html "shapely MultiPolygon documentation"
[pandas.DataFrame]: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html "pandas DataFrame documentation"