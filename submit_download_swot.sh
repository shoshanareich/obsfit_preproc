#!/bin/bash
#SBATCH -J swot_download
#SBATCH -o swot_download.%j.out
#SBATCH -e swot_download.%j.err
#SBATCH -N 1
#SBATCH -n 3 
#SBATCH -t 48:00:00

#date +%Y/%m/%d_%H:%M:%S.%3N >> regrid_swot_timing.txt

source activate py38

# Pull the Nth command from your commands.txt
#CMD=$(sed -n "${SLURM_ARRAY_TASK_ID}p" cycle9_labsea_runs)
#
#echo "Running task $SLURM_ARRAY_TASK_ID: $CMD"
#eval $CMD

python3 download_swot.py 18 &
python3 download_swot.py 19 &
python3 download_swot.py 20 &

# 'wait' tells the script to stay active until all background jobs finish
wait

#date +%Y/%m/%d_%H:%M:%S.%3N >> regrid_swot_timing.txt
