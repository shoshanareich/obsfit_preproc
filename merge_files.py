import os
import xarray as xr
import numpy as np
import pandas as pd

def load_netcdf_files(directory):
    files = [f for f in os.listdir(directory) if f.endswith('.nc')]
    datasets = [xr.open_dataset(os.path.join(directory, f)) for f in files]
    return datasets

def merge_per_cycle(directory):
    datasets = load_netcdf_files(directory)

    merged = None

    for ds in datasets:
        if merged is None:
            merged = ds
        elif len(ds.iOBS) > 0:
            merged = xr.concat([merged, ds], dim='iOBS')

    return merged


directory9 = '/nobackup/sreich/swot/swot_obsfit_L3/cycle_009_llc90_30'
#directory10 = '/nobackup/sreich/swot/swot_obsfit_L3/cycle_010_llc270_45'

merged9 = merge_per_cycle(directory9)
#merged10 = merge_per_cycle(directory10)

#ds_all = xr.concat([merged9, merged10], dim='iOBS')
ds_all = merged9

#half = range(0, int(1000000))
#ds_all = ds_all.isel(iOBS=half)

obs = xr.Dataset(
    data_vars=dict(
        obs_date           =(["iOBS"], ds_all.obs_date.values),
        obs_YYYYMMDD       =(["iOBS"], ds_all.obs_YYYYMMDD.values),
        obs_HHMMSS         =(["iOBS"], ds_all.obs_HHMMSS.values),
        sample_x           =(["iSAMPLE"], ds_all.sample_x.values),
        sample_y           =(["iSAMPLE"], ds_all.sample_y.values),
        sample_z           =(["iSAMPLE"], ds_all.sample_z.values),
        sample_type        =(["iSAMPLE"], ds_all.sample_type.values),
        obs_val            =(["iOBS"], ds_all.obs_val.values),
        obs_uncert         =(["iOBS"], np.ones(len(ds_all.sample_interp_i))*0.02),
        sample_interp_XC11 =(["iOBS"], ds_all.sample_interp_XC11.values ),
        sample_interp_YC11 =(["iOBS"], ds_all.sample_interp_YC11.values ),
        sample_interp_XCNINJ =(["iOBS"], ds_all.sample_interp_XCNINJ.values ),
        sample_interp_YCNINJ =(["iOBS"], ds_all.sample_interp_YCNINJ.values ),
        sample_interp_i =(["iOBS"], ds_all.sample_interp_i.values ),
        sample_interp_j =(["iOBS"], ds_all.sample_interp_j.values ),
        sample_interp_w =(["iOBS", "iINTERP"], np.ones((len(ds_all.sample_interp_i),8))/8  )
    ),
)


data_dir = '/nobackup/sreich/swot/swot_obsfit_L3/'
fname =  'swot_cycles_009_llc90_30_test_obsfit.nc'
obs.to_netcdf(data_dir + fname)
