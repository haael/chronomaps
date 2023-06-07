
1. Install Python packages.

`pip install netcdf`

`pip install geotiff`

`pip install imagecodecs`

`pip install pyshp`


2. Download data files.


Download and put all files under `data/` directory in the repository main directory.


2.1. Earth relief model

Go to: `https://www.ncei.noaa.gov/products/etopo-global-relief-model`.
Download "60 Arc-Second Resolution -> Bedrock elevation geotiff" (456MB).

2.2. Paleographic biome maps

Go to: `https://figshare.com/articles/dataset/LateQuaternary_Environment_nc/12293345/4`
Download "LateQuaternary_Environment.nc" (1.24GB).

2.3. Coastlines for different sea levels

Go to: `https://crc806db.uni-koeln.de/dataset/show/paleocoastlines-gis-dataset1462293239/`
Download "Paleocoastlines.zip" (45MB).


3. Generate tiles.

`./generate_biome_maps.py`
This will generate maps under `biome/` directory.


`./generate_topo_maps.py`
This will generate relief tiles under `topo/` directory. This process may take up to 2h.


4. Run the app.

`./chronomaps.py`

Requires Gtk3 that should come installed with your Linux distribution.


