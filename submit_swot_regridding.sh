#!/bin/bash
#PBS -N regrid_swot
#PBS -l select=1:ncpus=3:model=bro
#PBS -l walltime=00:10:00
#PBS -o outfile
#PBS -e errfile

source activate py38

limit stacksize unlimited

date +%Y/%m/%d_%H:%M:%S.%3N >> regrid_swot_timing.txt

#cd /home3/mgoldbe1/smart_cables/synthetic_data_extraction/
parallel --slf $PBS_NODEFILE -j 3 -a /home3/sreich/obsfit_prepoc/test_runs

date +%Y/%m/%d_%H:%M:%S.%3N >> regrid_swot_timing.txt
