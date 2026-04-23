import xarray as xr
import numpy as np
import pandas as pd

def datenum_xr(time_da):
    """Convert xarray datetime64 DataArray to MATLAB datenum."""
    # convert to numpy datetime64[ns]
    t = time_da.values.astype("datetime64[ns]")
    
    # to ordinal seconds since 1970-01-01
    secs = t.astype("datetime64[s]").astype(float)
    
    # convert to days
    days = secs / 86400.0
    
    # MATLAB datenum = days + offset (719529 is 1970-01-01 in MATLAB)
    return xr.DataArray(days + 719529, dims=time_da.dims, coords=time_da.coords)

def split_time_vars_int(time_da, fill_date=-9999, fill_time=-9999):
    # Flatten to 1D pandas Timestamps
    t = pd.to_datetime(time_da.values.ravel())

    # Initialize int arrays with fill values
    yyyymmdd = np.full(t.shape, fill_date, dtype="int64")
    hhmmss   = np.full(t.shape, fill_time, dtype="int64")

    mask = ~pd.isna(t)
    yyyymmdd[mask] = [int(ts.strftime("%Y%m%d")) for ts in t[mask]]
    hhmmss[mask]   = [int(ts.strftime("%H%M%S")) for ts in t[mask]]

    # Reshape back to original DataArray shape
    yyyymmdd = yyyymmdd.reshape(time_da.shape)
    hhmmss   = hhmmss.reshape(time_da.shape)

    # Wrap into DataArrays
    obs_YYYYMMDD = xr.DataArray(yyyymmdd, dims=time_da.dims, coords=time_da.coords)
    obs_HHMMSS   = xr.DataArray(hhmmss,   dims=time_da.dims, coords=time_da.coords)

    return obs_YYYYMMDD, obs_HHMMSS
