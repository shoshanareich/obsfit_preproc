# obsfit_preproc

Preprocessing pipeline that converts SWOT L3 sea surface height data into
MITgcm/pkg/obsfit/ NetCDF files for assimilation. This workflow
targets the Labrador Sea regional multigrid run (`regional_labsea/`); an
older global/LLC version is kept for reference (see bottom of this file).

## Environment

All regridding steps run in the `py38` conda env:

    source /home/shoshi/mambaforge/etc/profile.d/conda.sh
    conda activate /home/shoshi/mambaforge/envs/py38

Jobs are submitted to Slurm from this directory, so paths in the scripts
below assume `/home/shoshi/obsfit_preproc` and scratch space under
`/scratch/shoshi/swot/`.

## Workflow

### 1. Download SWOT L3 cycles

    sbatch submit_download_swot.sh

Before the first run on a given machine, export your AVISO FTP credentials
as environment variables (`download_swot.py` reads them via `os.environ`
rather than hardcoding them, since this file is tracked in git):

    export AVISO_USER="you@example.com"
    export AVISO_PASSWORD="..."

Add those two lines to a local, untracked file (e.g. `~/.bashrc` or a
`secrets.sh` you `source` before submitting) rather than committing them
anywhere in this repo.

Edits needed before submitting: `download_swot.py` is called once per cycle
inside `submit_download_swot.sh` (currently cycles 18, 19, 20 run in
parallel in the background). Update the cycle numbers there to fetch
different cycles. Files are pulled via FTP from the AVISO server
(`l3_lr_ssh/v3_0/Expert/reproc`) into `/scratch/shoshi/swot/L3v3/cycle<N>/`,
skipping files that already exist locally.

### 2. Build the per-file command list

    python3 filenames_hourly_map.py

Edit the `cycles` list and the resolution tag (`'HR'` or `'LR'`) at the top
of the script first. It walks `/scratch/shoshi/swot/L3v3/cycle<N>/`, finds
every file belonging to the requested cycle(s), and writes one line per
file to `cycle<N>_labsea_runs_L3v3` — each line is a full
`python3 regional_labsea/swot_to_obsfit_labsea.py <file> <res>` command.
This command-list file is what the Slurm array job below reads.

Resolution tag meaning (passed through to `swot_to_obsfit_labsea.py`):
- `HR` — higher density subsampling (tracks every 5 pixels, lines every 5)
- `LR` — coarser subsampling (tracks every 20, wider Gaussian filter)

### 3. Regrid each pass to obsfit format (Slurm array job)

    sbatch submit_swot_regridding.sh

Before submitting:
- Update the `CMD=...` path inside the script to point at the
  `cycle<N>_labsea_runs_L3v3` file built in step 2.
- Update `#SBATCH --array=1-N%60` so `N` matches the number of lines in
  that command-list file (one array task per file, max 60 running at once).

Each array task runs `regional_labsea/swot_to_obsfit_labsea.py <file> <res>`
on one SWOT pass file, which:
1. Loads the L3 Expert file for that pass from
   `/scratch/shoshi/swot/L3v3/cycle<N>/`.
2. Masks nadir points and crops to the Labrador Sea box
   (`lon: -80..-40`, `lat: 46..78`).
3. Keeps only best-quality points (`quality_flag == 0`) and forms
   `ssh = ssha_filtered + mdt`.
4. Runs a Gaussian filter (`apply_gaussian_filter.py`) to get a smoothed SSH
   and total uncertainty, dropping edge pixels and points with high
   variance (`sigma_total > 0.04`).
5. Subsamples onto a sparser track/line grid and computes along-track
   distance, track id, and line id (used later for PSD diagnostics).
6. Interpolates bathymetry from the `labsea_MG_12` grid and discards obs
   over water shallower than 200 m.
7. Writes one obsfit NetCDF per input pass to
   `/scratch/shoshi/swot/obsfit_labsea/cycle<N>_L3v3/`.

Regrid start/end timestamps for each job submission are logged to
`regrid_swot_timing.txt`.

### 4. Merge cycles into one obsfit file

    python3 merge_files.py

Edit the `glob.glob(...)` pattern at the top to select which cycles'
per-pass files (from step 3) to combine, and update the output filename at
the bottom to match (e.g. `swot_obsfit_cycles_9thru11_labsea_L3v3.nc`).
The script concatenates all per-pass files along `iOBS`, then moves the
per-sample metadata variables (`sample_lon`, `sample_lat`, `sample_depth`,
`sample_type`, `cycle`, `pass_no`, `track_id`, `line_id`,
`along_track_dist`) from the `iOBS` dimension onto a new `iSAMPLE`
dimension, and writes the combined file to
`/scratch/shoshi/swot/obsfit_labsea/`.

`merge_files.ipynb` is a notebook version of the same step, useful for
inspecting the merged dataset interactively.

## Directory contents

| Path | Purpose |
|---|---|
| `download_swot.py`, `submit_download_swot.sh` | Step 1: fetch L3 cycles from AVISO |
| `filenames_hourly_map.py` | Step 2: build per-cycle command list |
| `submit_swot_regridding.sh` | Step 3: Slurm array job driving the regrid |
| `regional_labsea/swot_to_obsfit_labsea.py` | Step 3: per-pass regrid to obsfit (Labrador Sea) |
| `regional_labsea/apply_gaussian_filter.py` | Gaussian smoothing + uncertainty used by the regrid script |
| `regional_labsea/date_utils.py` | obs date/time helpers (`datenum_xr`, `split_time_vars_int`) |
| `regional_labsea/diagnostics/` | scratch space for diagnostic plots/notebooks (currently empty) |
| `merge_files.py`, `merge_files.ipynb` | Step 4: merge per-pass files into one obsfit file |
| `cycle*_labsea_runs_L3v3`, `cycle9_labsea_runs(_LR)` | generated command-list files from step 2 (one per cycle/resolution run so far) |
| `regrid_swot_timing.txt` | timestamps logged on each regrid job submission |
| `jobfiles/` | Slurm stdout/stderr logs (gitignored) |
| `swot_to_obsfit_final_global.py`, `swot_ssh_utils.py`, `patchface3D.py` | legacy global/LLC-grid version of the pipeline, kept for reference — not part of the current Labrador Sea workflow |

## Notes / gotchas

- Hardcoded paths throughout (grid directories, `/scratch/shoshi/...`,
  `/home/shoshi/obsfit_preproc/...`) assume this exact user/filesystem
  layout — update them if moving to a new machine or scratch location.
- `swot_to_obsfit_labsea.py` infers `cycle` and `pass_no` from the SWOT
  filename itself (fields 5 and 6 of the underscore-delimited name), so the
  AVISO naming convention must stay consistent.
- The command-list files (`cycle<N>_labsea_runs_L3v3`) and the
  `--array=` range in `submit_swot_regridding.sh` must be regenerated/
  updated together each time you process a new cycle — nothing checks that
  the array size matches the file length.
