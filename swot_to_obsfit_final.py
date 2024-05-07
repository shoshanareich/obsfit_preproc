import numpy as np
import pandas as pd
import ecco_v4_py as ecco
import xarray as xr
from scipy.spatial import KDTree
import swot_ssh_utils as swot
import sys
sys.path.append('/home3/sreich/MITgcm_c68w/MITgcm/utils/python/MITgcmutils')
from MITgcmutils import rdmds

from patchface3D import *

### Load in LLC Grid ###

sNx = int(sys.argv[3])
sNy=sNx

grid_dir='/nobackup/sreich/llc1080_c68w_runs/run/'
hfc = rdmds(grid_dir+'hFacC', lev=0)
hfc[hfc!=0]=np.nan
# Convert to dict of 5 faces, sizes [(270,90), (270,90), (90,90), (90,270), (90,270)]
hfc_faces = ecco.llc_compact_to_faces(hfc, less_output=True)

xc = rdmds(grid_dir+'XC')
yc = rdmds(grid_dir+'YC')



### Read in SWOT Data from Input Args ###

pth = '/nobackup/sreich/swot/SWOT_L2_LR_SSH_2.0/Expert/'
filename = sys.argv[1] # sys.argv[0] is name of python file


ds_swot = xr.open_dataset(pth + filename)
ds_swot = ds_swot.drop_dims('num_sides')
ds_swot['longitude'] = (ds_swot['longitude'] + 180) % 360 - 180

ds_swot_sub = ds_swot.where(ds_swot.ancillary_surface_classification_flag == 0, drop=True)
swot_coords = np.c_[ds_swot_sub.latitude.values.ravel(), ds_swot_sub.longitude.values.ravel()]


# apply corrections
ssha = ds_swot_sub.ssha_karin_2
flag = ds_swot_sub.ancillary_surface_classification_flag
ssha = np.where(flag == 0, ssha, np.nan)

distance = ds_swot_sub.cross_track_distance.values

ssha = swot.fit_bias(
        ssha, distance,
        check_bad_point_threshold=0.1,
        remove_along_track_polynomial=True
    )

ds_swot_sub.ssha_karin_2.values = ssha

ssha[np.abs(ssha) > 0.3] = np.nan
ds_swot_sub.ssha_karin_2.values = ssha

ds_swot_sub['ssh_processed'] = ds_swot_sub.ssha_karin_2 + ds_swot_sub.mean_dynamic_topography


### Compute _interp fields ###

# reshape xc, yc from compact (13*nx, nx) form to worldmap view (nz=1,4*nx, 4*nx)
nx = int(sys.argv[2])

xc = rdmds(grid_dir+'XC')
yc = rdmds(grid_dir+'YC')

xc = patchface3D(xc,nx,1)
yc = patchface3D(yc,nx,1)

llc_coords = np.c_[yc.ravel(), xc.ravel()]

# compute nearest_swot_index relative to worldmap view
kd_tree = KDTree(llc_coords)
distance, nearest_swot_index_in_llc = kd_tree.query(swot_coords, k=1)

# transform xc and yc from worldmap (4*nx, 4*nx) to 5-face view
tileCount=0

xgrid = patchface3D_wrld_to_5f(xc)
ygrid = patchface3D_wrld_to_5f(yc)

for i in range(1,6):
    xgrid[i] = np.squeeze(xgrid[i])
    ygrid[i] = np.squeeze(ygrid[i])

XC11=dict(zip(range(1,6), [np.zeros_like(xgrid[i]) for i in range(1,6)]))
YC11=dict(zip(range(1,6), [np.zeros_like(xgrid[i]) for i in range(1,6)]))
XCNINJ=dict(zip(range(1,6), [np.zeros_like(xgrid[i]) for i in range(1,6)]))
YCNINJ=dict(zip(range(1,6), [np.zeros_like(xgrid[i]) for i in range(1,6)]))
iTile=dict(zip(range(1,6), [np.zeros_like(xgrid[i]) for i in range(1,6)]))
jTile=dict(zip(range(1,6), [np.zeros_like(xgrid[i]) for i in range(1,6)]))
tileNo=dict(zip(range(1,6), [np.zeros_like(xgrid[i]) for i in range(1,6)]))

# FOR face = 1..5: Do the [X,Y]C[11,NINJ] routine
for key in xgrid.keys():
    face_XC = xgrid[key] 
    face_YC = ygrid[key]
    for ii in range(int(face_XC.shape[1]/sNx)):
        for jj in range(int(face_XC.shape[0]/sNy)):
            tileCount += 1
            tmp_i = np.arange(sNx)+sNx*ii
            tmp_j = np.arange(sNy)+sNx*jj
            tmp_XC = face_XC[ np.ix_( tmp_j, tmp_i ) ]
            tmp_YC = face_YC[ np.ix_( tmp_j, tmp_i ) ]
            XC11[key][ np.ix_( tmp_j, tmp_i ) ] = tmp_XC[0,0]
            YC11[key][ np.ix_( tmp_j, tmp_i ) ] = tmp_YC[0,0]
            XCNINJ[key][ np.ix_( tmp_j, tmp_i ) ] = tmp_XC[-1,-1]
            YCNINJ[key][ np.ix_( tmp_j, tmp_i ) ] = tmp_YC[-1,-1]
            iTile[key][ np.ix_( tmp_j, tmp_i ) ] = np.ones((sNx,1)) * np.arange(1,sNy+1)
            jTile[key][ np.ix_( tmp_j, tmp_i ) ] = (np.arange(1,sNx+1) * np.ones((sNy,1))).T
            tileNo[key][ np.ix_( tmp_j, tmp_i ) ] = tileCount*np.ones((sNy,sNx))

tile_keys = ['XC11', 'YC11', 'XCNINJ', 'YCNINJ', 'i', 'j']
tile_vals = [XC11, YC11, XCNINJ, YCNINJ, iTile, jTile]
tile_data_in = dict(zip(tile_keys, tile_vals))
tile_dict = dict()
for key in tile_keys:

    # - Line 68: sneakily turn each [X,Y]C[11,NINJ] field from 5-face  to compact
    temp = tile_data_in[key]
    temp = np.concatenate((temp[1], temp[2], temp[3], temp[4].T, temp[5].T))

    # - Line 69: Change each field from compact to worldmap (she has done so in her python function)
    tile_data_in[key] = patchface3D(temp,nx,1)

    # - Line 70: Use the obs_point (which was created relative to worldmap view) to grab the index from each field, 
    # which are now properly in worldmap view.
    tile_dict['sample_interp_' + key] = tile_data_in[key].ravel()[nearest_swot_index_in_llc]



### Add obs_interp_ fields to data ###

# reshape for num_lines, num_pixels
for key in tile_dict.keys():
    tile_dict[key] = tile_dict[key].reshape(ds_swot_sub.ssh_karin_2.shape)

# add interp fields to xarray
for key, item in tile_dict.items():
    dims = ('num_lines', 'num_pixels')  # Replace with your actual dimension names
    var_da = xr.DataArray(item, dims=dims, name=key)
    ds_swot_sub[key] = var_da


# up until this point, we have obsfit fields for each individual swot point
# now can group and average all swot ssha values in same llc grid square

df_swot = ds_swot_sub.to_dataframe()
gb = df_swot.groupby(['sample_interp_XC11', 'sample_interp_YC11', 'sample_interp_XCNINJ', 'sample_interp_YCNINJ', 'sample_interp_i', 'sample_interp_j'])
counts = gb.size().to_frame(name='counts')
gb_stats = (counts
.join(gb.agg({'ssha_karin_2': 'mean'}).rename(columns={'ssh_processed': 'obs_val'}))
.join(gb.agg({'ssha_karin_2': 'std'}).rename(columns={'ssha_karin_2': 'ssha_karin_2_std'}))
.join(gb.agg({'latitude': 'mean'}).rename(columns={'latitude': 'sample_x'}))
.join(gb.agg({'longitude': 'mean'}).rename(columns={'longitude': 'sample_y'}))
.join(gb.agg({'time': 'mean'}).rename(columns={'time': 'time_mean'}))
#.join(gb.agg({'time': 'std'}).rename(columns={'time': 'time_std'}))
.reset_index()
)


### Create obsfit xarray ###
from datetime import datetime as dt

def datenum(d):
    return 366 + d.toordinal() + (d - dt.fromordinal(d.toordinal())).total_seconds()/(24*60*60)

gb_stats = gb_stats[~np.isnan(gb_stats['obs_val'])]

gb_stats['obs_date'] = pd.to_datetime(gb_stats['time_mean']).apply(lambda x: datenum(x))
gb_stats['obs_YYYYMMDD'] = gb_stats['time_mean'].apply(lambda x: int(x.strftime('%Y%m%d')))
gb_stats['obs_HHMMSS'] = gb_stats['time_mean'].apply(lambda x: int(x.strftime('%H%M%S')))


obs_weight = np.ones(len(gb_stats.sample_y.values))

obs = xr.Dataset(
    data_vars=dict(
        obs_date           =(["iOBS"], gb_stats.obs_date.values),
        obs_YYYYMMDD       =(["iOBS"], gb_stats.obs_YYYYMMDD.values),
        obs_HHMMSS         =(["iOBS"], gb_stats.obs_HHMMSS.values), 
#        sample_x           =(["iSAMPLE"], gb_stats.sample_x.values),
#        sample_y           =(["iSAMPLE"], gb_stats.sample_y.values),
#        sample_z           =(["iSAMPLE"], np.zeros(len(gb_stats.sample_y.values))),
#        sample_type        =(["iSAMPLE"], 5*np.ones(len(gb_stats.sample_y.values))),
        sample_x           =(["iOBS"], gb_stats.sample_x.values),
        sample_y           =(["iOBS"], gb_stats.sample_y.values),
        sample_z           =(["iOBS"], np.zeros(len(gb_stats.sample_y.values))),
        sample_type        =(["iOBS"], 5*np.ones(len(gb_stats.sample_y.values))),
        obs_val            =(["iOBS"], gb_stats.obs_val.values),
        obs_uncert         =(["iOBS"], np.sqrt(1/obs_weight)),
        sample_interp_XC11 =(["iOBS"], gb_stats.sample_interp_XC11.values ),
        sample_interp_YC11 =(["iOBS"], gb_stats.sample_interp_YC11.values ),
        sample_interp_XCNINJ =(["iOBS"], gb_stats.sample_interp_XCNINJ.values ),
        sample_interp_YCNINJ =(["iOBS"], gb_stats.sample_interp_YCNINJ.values ),
        sample_interp_i =(["iOBS"], gb_stats.sample_interp_i.values ),
        sample_interp_j =(["iOBS"], gb_stats.sample_interp_j.values ),
#        sample_interp_w =(["iOBS", "iINTERP"], np.ones((len(gb_stats.sample_interp_i),8))/8  )
    ),
)

obs = obs.assign_coords({'longitude': obs.sample_x, 'latitude': obs.sample_y})


data_dir = '/nobackup/sreich/swot/swot_obsfit_L2/'
fname = filename.split('.')[0] + '_obsfit.nc'
obs.to_netcdf(data_dir + fname)





