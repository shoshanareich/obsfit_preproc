import os
import glob
import xarray as xr
import numpy as np


# Get a list of all NetCDF files
#files = sorted(glob.glob("/scratch/shoshi/swot/obsfit_labsea/cycle1[2-4]_L3v3/*.nc"))
files = sorted(glob.glob("/scratch/shoshi/swot/obsfit_labsea/cycle1[8-9]_L3v3/*.nc") + glob.glob("/scratch/shoshi/swot/obsfit_labsea/cycle20_L3v3/*.nc"))

# Open all files as a list of xarray datasets
datasets = [xr.open_dataset(f) for f in files]

# Concatenate along iOBS
# Note: concat will automatically include cycle, pass_no, track_id, line_id, and along_track_dist 
ds = xr.concat(datasets, dim="iOBS", data_vars="all", coords="all", compat="override")

# Get length of iOBS
nobs = ds.dims["iOBS"]

# Add a new dimension iSAMPLE (no coordinate attached)
ds = ds.expand_dims({"iSAMPLE": nobs}).isel(iSAMPLE=0)  # makes empty dim
ds = ds.assign_coords()  # remove automatic coordinate assignment

# Now reassign variables from iOBS -> iSAMPLE
vars_to_move = [
    "sample_lon", 
    "sample_lat", 
    "sample_depth", 
    "sample_type",
    "cycle",
    "pass_no",
    "track_id",
    "line_id",
    "along_track_dist"
]

for v in vars_to_move:
    if v in ds:
        ds[v] = xr.DataArray(
            ds[v].values,
            dims=("iSAMPLE",),   # put it on iSAMPLE, not iOBS
        )
        ds[v].attrs.update({"note": f"moved from iOBS to iSAMPLE"})

ds.to_netcdf("/scratch/shoshi/swot/obsfit_labsea/swot_obsfit_cycles_18thru20_labsea_L3v3.nc")
