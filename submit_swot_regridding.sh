#!/bin/bash
#PBS -N regrid_swot
#PBS -l select=1:ncpus=3:model=bro
#PBS -l walltime=00:05:00
#PBS -o outfile
#PBS -e errfile


limit stacksize unlimited

date +%Y/%m/%d_%H:%M:%S.%3N >> regrid_swot_timing.txt

module use -a /swbuild/analytix/tools/modulefiles
module load miniconda3/v4
source activate py38

#cd /home3/mgoldbe1/smart_cables/synthetic_data_extraction/
parallel --slf $PBS_NODEFILE -j 3 -a /home3/sreich/obsfit_preproc/test_runs

date +%Y/%m/%d_%H:%M:%S.%3N >> regrid_swot_timing.txt
