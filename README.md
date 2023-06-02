
1. Install Python packages.

`pip3 install netcdf`
`pip3 install geotiff`
`pip3 install imagecodecs`


2. Download data files.

Go to: `https://www.ncei.noaa.gov/products/etopo-global-relief-model`.
Download "60 Arc-Second Resolution -> Bedrock elevation geotiff" (456MB).

Go to: `https://figshare.com/articles/dataset/LateQuaternary_Environment_nc/12293345/4`
Download "LateQuaternary_Environment.nc" (1.24GB).

Put all files under `data/` directory in the repository main directory.


3. Generate tiles.

`./generate_biome_maps.py`
This will generate maps under `biome/` directory.


`./generate_topo_maps.py`
This will generate relief tiles under `topo/` directory. This process may take up to 2h.


4. Run the app.

`./chronomaps.py`

Requires Gtk3 that should come installed with your Linux distribution.


