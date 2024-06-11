import os

# user defined SWOT cycles\
cycles = [10]
sNx = 30 #180
Nx = 270 #1080

with open("cycle10_270_30_runs", "w", newline = '') as a:
    for path, sub_dirs, files in os.walk('/nobackup/sreich/swot/L3_aviso/cycle_010'):

        # check if file is in desired cycles\
        for filename in sorted(files):

            file_cycle = int(filename.split('_')[5])

            if file_cycle in cycles:
                f = filename
                # write to execute python script
                a.write('source activate py38; python3 -u /home3/sreich/obsfit_preproc/swot_to_obsfit_final.py ')
                a.write(str(f) + ' ' + str(Nx) + ' ' + str(sNx))
        
                # new line
                a.write(os.linesep)
                
