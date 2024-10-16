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

#grid_dir='/nobackup/sreich/llc1080_c68w_runs/run/'
#grid_dir='/nobackup/sreich/llc270_c68w_runs/run_pk0000841536_1200s_tidesOFF/'
grid_dir='/nobackup/sreich/multigrid_jpl_obsfit/llc90/run.v4_rls4.077d3.iter0.swot1992.fwd/'
hfc = rdmds(grid_dir+'hFacC', lev=0)
hfc[hfc!=0]=np.nan
# Convert to dict of 5 faces, sizes [(270,90), (270,90), (90,90), (90,270), (90,270)]
hfc_faces = ecco.llc_compact_to_faces(hfc, less_output=True)

xc = rdmds(grid_dir+'XC')
yc = rdmds(grid_dir+'YC')



### Read in SWOT Data from Input Args ###

pth = '/nobackup/sreich/swot/L3_aviso/cycle_009/'
filename = sys.argv[1] # sys.argv[0] is name of python file


ds_swot = xr.open_dataset(pth + filename)
ds_swot = ds_swot.drop_dims('num_nadir')
ds_swot['longitude'] = (ds_swot['longitude'] + 180) % 360 - 180

swot_coords = np.c_[ds_swot.latitude.values.ravel(), ds_swot.longitude.values.ravel()]


# apply corrections if using L2 data
if 'L2' in filename:
    ssha = ds_swot.ssha_karin_2
    flag = ds_swot.ancillary_surface_classification_flag
    ssha = np.where(flag == 0, ssha, np.nan)
    
    distance = ds_swot.cross_track_distance.values
    
    ssha = swot.fit_bias(
            ssha, distance,
            check_bad_point_threshold=0.1,
            remove_along_track_polynomial=True
        )

    ssha[np.abs(ssha) > 0.3] = np.nan
    ds_swot.ssha_karin_2.values = ssha
    
    ds_swot['ssh_processed'] = ds_swot.ssha_karin_2 + ds_swot.mean_dynamic_topography
    

#### nadir already removed?? ####
ssha = ds_swot['ssha'].values

mask = (ds_swot['quality_flag'] == 0).values
ssha = mask * ssha

ssha[np.abs(ssha) > 0.3] = np.nan

ds_swot['ssh'] = ssha + ds_swot.mdt



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


def get_tile_dict(xc, yc, prof_point, sNx, sNy):
    def make_empty_5f(xgrid):
        tmp = dict();
        for face in range(1, 6): tmp[face] = np.zeros_like(xgrid[face])
        return tmp

    
    # transform xc and yc from worldmap back to 5faces
    #xc_5faces = patchface3D_wrld_to_5f(xc[np.newaxis, :, :])
    #yc_5faces = patchface3D_wrld_to_5f(yc[np.newaxis, :, :])
    xc_5faces = patchface3D_wrld_to_5f(xc)
    yc_5faces = patchface3D_wrld_to_5f(yc)

    xgrid = xc_5faces.copy()
    ygrid = yc_5faces.copy()

    XC11 = make_empty_5f(xgrid)
    YC11 = make_empty_5f(xgrid)
    XCNINJ = make_empty_5f(xgrid)
    YCNINJ = make_empty_5f(xgrid)
    iTile = make_empty_5f(xgrid)
    jTile = make_empty_5f(xgrid)
    tileNo = make_empty_5f(xgrid)

    tileCount=0
    for iF in range(1, len(xgrid)+1):
        face_XC = xgrid[iF][0]
        face_YC = ygrid[iF][0]
        for ii in range(face_XC.shape[0] // sNx):
            for jj in range(face_XC.shape[1] // sNy):
                tileCount += 1
                tmp_i = slice(sNx * ii, sNx * (ii + 1))
                tmp_j = slice(sNy * jj, sNy * (jj + 1))
                tmp_XC = face_XC[tmp_i, tmp_j]
                tmp_YC = face_YC[tmp_i, tmp_j]
                XC11[iF][0][tmp_i, tmp_j] = tmp_XC[0, 0]
                YC11[iF][0][tmp_i, tmp_j] = tmp_YC[0, 0]
                XCNINJ[iF][0][tmp_i, tmp_j] = tmp_XC[-1, -1]
                YCNINJ[iF][0][tmp_i, tmp_j] = tmp_YC[-1, -1]
                iTile[iF][0][tmp_i, tmp_j] = np.outer(np.ones(sNx), np.arange(1, sNy + 1))
                jTile[iF][0][tmp_i, tmp_j] = np.outer(np.arange(1, sNx + 1), np.ones(sNy))
                tileNo[iF][0][tmp_i, tmp_j] = tileCount * np.ones((sNx, sNy))


    tile_keys = ['XC11', 'YC11', 'XCNINJ', 'YCNINJ', 'i', 'j']


    XC11 = patchface3D_5f_to_wrld(XC11)[0,:,:]
    YC11 = patchface3D_5f_to_wrld(YC11)[0,:,:]
    XCNINJ = patchface3D_5f_to_wrld(XCNINJ)[0,:,:]
    YCNINJ = patchface3D_5f_to_wrld(YCNINJ)[0,:,:]
    iTile = patchface3D_5f_to_wrld(iTile)[0,:,:]
    jTile = patchface3D_5f_to_wrld(jTile)[0,:,:]

    tile_vals = [XC11, YC11, XCNINJ, YCNINJ, iTile, jTile]

    tile_dict = dict()
    for key, val in zip(tile_keys, tile_vals):
        tile_dict['sample_interp_' + key] = val.ravel()[prof_point]
    return tile_dict


tile_dict = get_tile_dict(xc, yc, nearest_swot_index_in_llc, sNx, sNy)

### Add obs_interp_ fields to data ###

# reshape for num_lines, num_pixels
for key in tile_dict.keys():
    tile_dict[key] = tile_dict[key].reshape(ds_swot.ssha.shape)

# add interp fields to xarray
for key, item in tile_dict.items():
    dims = ('num_lines', 'num_pixels')  # Replace with your actual dimension names
    var_da = xr.DataArray(item, dims=dims, name=key)
    ds_swot[key] = var_da


# up until this point, we have obsfit fields for each individual swot point
# now can group and average all swot ssha values in same llc grid square

df_swot = ds_swot.to_dataframe()
gb = df_swot.groupby(['sample_interp_XC11', 'sample_interp_YC11', 'sample_interp_XCNINJ', 'sample_interp_YCNINJ', 'sample_interp_i', 'sample_interp_j'])
counts = gb.size().to_frame(name='counts')
gb_stats = (counts
.join(gb.agg({'ssh': 'mean'}).rename(columns={'ssh': 'obs_val'}))
.join(gb.agg({'ssh': 'std'}).rename(columns={'ssh': 'ssh_std'}))
.join(gb.agg({'latitude': 'mean'}).rename(columns={'latitude': 'sample_y'}))
.join(gb.agg({'longitude': 'mean'}).rename(columns={'longitude': 'sample_x'}))
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


data_dir = '/nobackup/sreich/swot/swot_obsfit_L3/cycle_009_llc90_30/'
fname = filename.split('.')[0] + '_obsfit.nc'
obs.to_netcdf(data_dir + fname)


print('done ' + fname)


