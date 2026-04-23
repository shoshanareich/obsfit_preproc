#!/bin/bash
#SBATCH -J swot_preproc 
#SBATCH -o swot_preproc.%j.out
#SBATCH -e swot_preproc.%j.err
#SBATCH -N 1 
#SBATCH -n 1
#SBATCH -t 1:00:00
#SBATCH --cpus-per-task=1
#SBATCH --array=1-578%60

set -eo pipefail

date +%Y/%m/%d_%H:%M:%S.%3N >> regrid_swot_timing.txt

source /home/shoshi/mambaforge/etc/profile.d/conda.sh
conda activate /home/shoshi/mambaforge/envs/py38

# Get the command for this array index
CMD=$(sed -n "${SLURM_ARRAY_TASK_ID}p" \
    /home/shoshi/obsfit_preproc/cycle20_labsea_runs_L3v3)

echo "[$(date)] Running task ${SLURM_ARRAY_TASK_ID}"
echo "$CMD"

eval "$CMD"

#parallel -j $SLURM_CPUS_ON_NODE -a /home/shoshi/obsfit_preproc/cycle11_labsea_runs_L3v3
#/usr/bin/parallel -j $SLURM_CPUS_ON_NODE -a /home/shoshi/obsfit_preproc/cycle11_labsea_runs_L3v3

