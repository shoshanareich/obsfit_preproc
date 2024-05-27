#!/bin/bash
#PBS -N regrid_swot
#PBS -q devel
#PBS -l select=4:ncpus=28:model=bro
#PBS -l walltime=02:00:00
#PBS -o outfile
#PBS -e errfile

cd $PBS_O_WORKDIR

limit stacksize unlimited

date +%Y/%m/%d_%H:%M:%S.%3N >> regrid_swot_timing.txt

./usr/local/lib/init/global.profile
module use -a /swbuild/analytix/tools/modulefiles
module load miniconda3/v4
source activate py38

/nasa/pkgsrc/toss4/2023Q3/bin/parallel -j 14 --slf $PBS_NODEFILE -a /home3/sreich/obsfit_preproc/cycle10_runs

date +%Y/%m/%d_%H:%M:%S.%3N >> regrid_swot_timing.txt
