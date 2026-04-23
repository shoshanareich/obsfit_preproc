import os

# user defined SWOT cycles\
cycles = [20]
#sNx = 180
#Nx = 1080

with open("cycle20_labsea_runs_L3v3", "w", newline = '') as a:
    for path, sub_dirs, files in os.walk('/scratch/shoshi/swot/L3v3/cycle20'): #os.walk('./data/SWOT_SIMULATED_L2_KARIN_SSH_GLORYS_SCIENCE_V1'):\

        # check if file is in desired cycles\
        for filename in sorted(files):

            file_cycle = int(filename.split('_')[5])

            if file_cycle in cycles:
                f = filename
                # write to execute python script
                a.write('python3 -u /home/shoshi/obsfit_preproc/regional_labsea/swot_to_obsfit_labsea.py ')
                a.write(str(f) + ' ' + 'HR') # LR for lo-res or HR for high-res #str(Nx) + ' ' + str(sNx))
        
                # new line
                a.write(os.linesep)
                
