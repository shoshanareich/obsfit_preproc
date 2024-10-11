#!/bin/bash
#PBS -N regrid_swot
#PBS -q devel
#PBS -l select=4:ncpus=28:model=bro
#PBS -l walltime=02:00:00
#PBS -o outfile
#PBS -e errfile

cd $PBS_O_WORKDIR

limit stacksize unlimited

./usr/local/lib/init/global.profile
module use -a /swbuild/analytix/tools/modulefiles
module load miniconda3/v4
source activate py38

# 1. create text file which lists the python commands to execute
python3 /home3/sreich/obsfit_preproc/filenames_hourly_map.py

# 2. run regridding for all files individually

date +%Y/%m/%d_%H:%M:%S.%3N >> regrid_swot_timing.txt

/nasa/pkgsrc/toss4/2023Q3/bin/parallel -j 14 --slf $PBS_NODEFILE -a /home3/sreich/obsfit_preproc/cycle9_90_30_runs

date +%Y/%m/%d_%H:%M:%S.%3N >> regrid_swot_timing.txt

# 3. combine swot hourly files
python3 /home3/sreich/obsfit_preproc/merge_files.py

