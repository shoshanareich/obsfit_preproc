#!/bin/bash
#PBS -N regrid_swot
#PBS -l select=21:ncpus=28:model=bro
#PBS -l walltime=00:15:00
#PBS -o outfile
#PBS -e errfile


limit stacksize unlimited

date +%Y/%m/%d_%H:%M:%S.%3N >> regrid_swot_timing.txt

module use -a /swbuild/analytix/tools/modulefiles
module load miniconda3/v4
source activate py38

#cd /home3/mgoldbe1/smart_cables/synthetic_data_extraction/
parallel --slf $PBS_NODEFILE -j 28 -a /home3/sreich/obsfit_preproc/cycle9_runs

date +%Y/%m/%d_%H:%M:%S.%3N >> regrid_swot_timing.txt
