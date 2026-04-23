import sys
import os
from ftplib import FTP

host = "ftp-access.aviso.altimetry.fr"
user = "sreich@utexas.edu"
password = "IqannU"

cycle_num=sys.argv[1]

base_path = "/swot_products/l3_karin_nadir/l3_lr_ssh/v3_0"
local_path = f'/scratch/shoshi/swot/L3v3/cycle{cycle_num}'  

# Ensure local directory exists
os.makedirs(local_path, exist_ok=True)

# Connect to FTP
ftp = FTP()
ftp.connect(host=host, port=21, timeout=30)
ftp.login(user, password)

# Navigate to remote directory
ftp.cwd(base_path + f'/Expert/reproc/cycle_0{cycle_num}')

# List remote files
files = ftp.nlst()
print("Found", len(files), "files.")

# Download files if not already present
for filename in files:
    local_file = os.path.join(local_path, filename)
    
    if os.path.exists(local_file):
        print(f"Skipping {filename}, already exists.")
        continue
    
    print(f"Downloading: {filename} → {local_file}")
    with open(local_file, "wb") as f:
        ftp.retrbinary(f"RETR {filename}", f.write)

ftp.quit()
print("Done.")

