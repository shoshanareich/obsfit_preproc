import numpy as np
import xarray as xr
import xmitgcm
import sys
import os 
import apply_gaussian_filter as agf
from date_utils import datenum_xr, split_time_vars_int
sys.path.append('/home/shoshi/MITgcm_c68r/MITgcm/utils/python/MITgcmutils')
from MITgcmutils import rdmds

# Helper Function for Distance
def calc_along_track_dist(lats, lons):
    """
    Computes cumulative distance along a track in kilometers using Haversine.
    """
    from math import radians, cos, sin, asin, sqrt
    
    def haversine(lon1, lat1, lon2, lat2):
        r = 6371 # radius of earth in km
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        return c * r

    distances = [0]
    for i in range(1, len(lats)):
        dist = haversine(lons[i-1], lats[i-1], lons[i], lats[i])
        distances.append(distances[-1] + dist)
    return np.array(distances)



local_filepath='/scratch/shoshi/swot/L3v3/cycle20/'
localbox=[-80+360, -40+360, 46, 78] # Labrador Sea

filename = sys.argv[1]
pass_no = filename.split('_')[6]
cycle = filename.split('_')[5]

res = sys.argv[2]

# read in data

ds_expert = xr.open_dataset(local_filepath + filename)
#ds_expert = ds_expert.assign_coords(longitude=(((ds_expert.longitude + 180) % 360) - 180))


# remove nadir
mask = np.zeros(ds_expert.ssha_filtered.shape, dtype=bool)
mask[ds_expert.i_num_line, ds_expert.i_num_pixel] = True
ds_expert = ds_expert.assign(ssha_filtered=ds_expert.ssha_filtered.where(~mask, np.nan))

# Select data over the region
localsubset = (
(ds_expert.longitude > localbox[0]) &
(ds_expert.longitude < localbox[1]) &
(ds_expert.latitude > localbox[2]) &
(ds_expert.latitude < localbox[3]))

if localsubset.any():
    ds_expert_sub = ds_expert.where(localsubset, drop=True)
    if np.isnan(ds_expert_sub.ssha_filtered).all():
        print(f'pass {pass_no}: all nans')
        sys.exit(0)
    else:
        print(f'pass {pass_no}: processing')
else:
    print(f"pass {pass_no}: no data in local subset")
    ds_expert_sub = None
    sys.exit(0)


#ds_expert_sub = ds_expert.where(localsubset, drop=True)

# only keep best quality data
mask = (ds_expert_sub.quality_flag == 0) & (~np.isnan(ds_expert_sub.quality_flag))
ds_expert_sub['ssha_filtered'] = ds_expert_sub.ssha_filtered.where(mask)

ds_expert_sub["ssh"] = ds_expert_sub.ssha_filtered + ds_expert_sub.mdt


# apply gaussian filter
if res == 'LR':
    sigma = 8
    half_width = 8
elif res == 'HR':
    sigma = 2
    half_width = 2
else:
    print('res misspecified. using default sigma and half_width (2)')

sigma_total, sigma_instr_smoothed, sigma_rep, filtered = agf.data_uncertainty(ds_expert_sub["ssh"], sigma=sigma, half_width=half_width)
# remove extra pixels
filtered[:,:3] = np.nan
filtered[:, 30:38] = np.nan
filtered[:,-4:] = np.nan

sigma_total[:,:3] = np.nan
sigma_total[:, 30:38] = np.nan
sigma_total[:,-4:] = np.nan

ds_expert_sub["ssh_filtered"] = (('num_lines', 'num_pixels'), filtered)
ds_expert_sub["ssh_sigma_total"] = sigma_total

# get rid of points with high variance (mainly on top and bottom edges)
ds_expert_sub['ssh_filtered'] = ds_expert_sub['ssh_filtered'].where(ds_expert_sub['ssh_sigma_total'] <= 0.04, np.nan)
ds_expert_sub['ssh_sigma_total'] = ds_expert_sub['ssh_sigma_total'].where(ds_expert_sub['ssh_sigma_total'] <= 0.04, np.nan)

# subsample to every 10km or 5 grid points
# only tracks in interior
if res == 'LR':
    tracks = [16, 51]
    lines = ds_expert_sub.num_lines.values[20:-20:20]
elif res == 'HR':
    tracks = [5, 10, 15, 20, 25, 42, 47, 52, 57, 62]
    lines = ds_expert_sub.num_lines.values[5:-5:5]
else:
    print('res misspecified')


ds_sub = ds_expert_sub.isel(num_lines=lines, num_pixels=tracks)
ds_sub = ds_sub.where(ds_sub.ssh_filtered > -9000, drop=True)

# Geometry Metadata and Distance
num_lines_shape = ds_sub.ssh_filtered.shape[0]
num_pixels_shape = ds_sub.ssh_filtered.shape[1]

line_indices, track_indices = np.meshgrid(
    np.arange(num_lines_shape), 
    np.arange(num_pixels_shape), 
    indexing='ij'
)

dist_2d = np.zeros_like(ds_sub.ssh_filtered.values)
for t in range(num_pixels_shape):
    track_lats = ds_sub.latitude.values[:, t]
    track_lons = ds_sub.longitude.values[:, t]
    dist_2d[:, t] = calc_along_track_dist(track_lats, track_lons)

ds_sub['track_id'] = (('num_lines', 'num_pixels'), track_indices)
ds_sub['line_id'] = (('num_lines', 'num_pixels'), line_indices)
ds_sub['along_track_dist'] = (('num_lines', 'num_pixels'), dist_2d)



# create obsfit object
ds_sub['obs_date'] = datenum_xr(ds_sub["time"])

obs_YYYYMMDD, obs_HHMMSS = split_time_vars_int(ds_sub["time"])
ds_sub["obs_YYYYMMDD"] = obs_YYYYMMDD
ds_sub["obs_HHMMSS"]   = obs_HHMMSS

ds_obsfit = xr.Dataset(
    data_vars=dict(
        obs_YYYYMMDD       =(["iOBS"], ds_sub.obs_YYYYMMDD.values.ravel()),
        obs_HHMMSS         =(["iOBS"], ds_sub.obs_HHMMSS.values.ravel()),
#        sample_type        =(["iSAMPLE"], 5*np.ones(len(ds_sub.ssh_filtered.values.ravel()))),
#        sample_lon         =(["iSAMPLE"], ds_sub.longitude.values.ravel()),
#        sample_lat         =(["iSAMPLE"], ds_sub.latitude.values.ravel()),
#        sample_depth       =(["iSAMPLE"], np.zeros(len(ds_sub.ssh_filtered.values.ravel()))),
        sample_type        =(["iOBS"], 5*np.ones(len(ds_sub.ssh_filtered.values.ravel()))),
        sample_lon         =(["iOBS"], ds_sub.longitude.values.ravel()),
        sample_lat         =(["iOBS"], ds_sub.latitude.values.ravel()),
        sample_depth       =(["iOBS"], np.zeros(len(ds_sub.ssh_filtered.values.ravel()))),
        obs_val            =(["iOBS"], ds_sub.ssh_filtered.values.ravel()),
        obs_uncert         =(["iOBS"], ds_sub.ssh_sigma_total.values.ravel()),
        # Metadata for Spectral Analysis
        cycle              =(["iOBS"], np.full(ds_sub.ssh_filtered.values.ravel().shape, int(cycle))),
        pass_no            =(["iOBS"], np.full(ds_sub.ssh_filtered.values.ravel().shape, int(pass_no))),
        track_id           =(["iOBS"], ds_sub.track_id.values.ravel()),
        line_id            =(["iOBS"], ds_sub.line_id.values.ravel()),
        along_track_dist   =(["iOBS"], ds_sub.along_track_dist.values.ravel()),
    ),
)

ds_obsfit = ds_obsfit.assign_coords({'longitude': ds_obsfit.sample_lon, 'latitude': ds_obsfit.sample_lat})
ds_obsfit['obs_val'] = ds_obsfit['obs_val'].fillna(-9999)
ds_obsfit['obs_uncert'] = ds_obsfit['obs_uncert'].fillna(-9999)


## discard points where depth is <200m
lon = ds_obsfit.sample_lon.values
lat = ds_obsfit.sample_lat.values
obs_val = ds_obsfit.obs_val.values

grid_dir = '/scratch/shoshi/labsea_MG_12/grid_lores/'
grid = xmitgcm.open_mdsdataset(grid_dir, iters=None)

depth = rdmds('/scratch/shoshi/labsea_MG_12/grid_lores_cleanbathy/' + 'Depth')

grid.Depth.values = depth

depth_at_obs = grid.Depth.interp(
    XC=xr.DataArray(ds_obsfit.longitude, dims='iOBS'),
    YC=xr.DataArray(ds_obsfit.latitude, dims='iOBS')
)

# Now mask obs_val where depth < 200
ds_obsfit['obs_val'] = xr.where(depth_at_obs >= 200, ds_obsfit.obs_val, -9999)

ds_obsfit = ds_obsfit.where(ds_obsfit.obs_val > -9000, drop=True)

# write out
data_dir = '/scratch/shoshi/swot/obsfit_labsea/cycle20_L3v3/'
os.makedirs(data_dir, exist_ok=True)
fname = filename.split('.')[0] + '_obsfit.nc'
ds_obsfit.to_netcdf(data_dir + fname)
