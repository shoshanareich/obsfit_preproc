import numpy as np
import sys
sys.path.append('/home/shoshi/MITgcm_c68p/MITgcm/utils/python/MITgcmutils')

from MITgcmutils import rdmds




### compact --> worldmap view ###

# taken from /home/atnguyen/python/read_simple_ocellc90global.py
def patchface3D(fldin,nx,nz):

    print(nz)
    #add a new dimension in case it's only 2d field:
    if nz == 1:
        fldin=fldin[np.newaxis, :, :]

    #defining a big face:
    a=np.zeros((nz,4*nx,4*nx))       #(50,270,360)

    #face1
    tmp=fldin[:,0:3*nx,0:nx]        #(50,270,90)
    a[:,0:3*nx,0:nx]=tmp

    #face2
    tmp=fldin[:,(3*nx):(6*nx),0:nx] #(50, 270,90)
    a[:,0:3*nx,nx:2*nx]=tmp

    #face3
    tmp=fldin[:,(6*nx):(7*nx),0:nx] #(50, 90, 90)
    tmp=np.transpose(tmp, (1,2,0))  #(90, 90, 50)
    ##syntax to rotate ccw:
    tmp1=list(zip(*tmp[::-1]))
    tmp1=np.asarray(tmp1)
    tmp1=np.transpose(tmp1,[2,0,1]) #(50, 90, 90)
    a[:,3*nx:4*nx,0:nx]=tmp1

    #face4
    tmp=np.reshape(fldin[:,7*nx:10*nx,0:nx],[nz,nx,3*nx]) #(50,90,270)
    tmp=np.transpose(tmp, (1,2,0))
    print(tmp.shape)                                      #(90,270,50)
    #syntax to rotate cw:
    tmp1=list(zip(*tmp))[::-1]      #type is <class 'list'>
    tmp1=np.asarray(tmp1)           #type <class 'numpy.ndarray'>, shape (270,90,50)
    tmp1=np.transpose(tmp1,[2,0,1]) #(50,270,90)
    a[:,0:3*nx,2*nx:3*nx]=tmp1

    #face5
    tmp=np.reshape(fldin[:,10*nx:13*nx,0:nx],[nz,nx,3*nx]) #(50,90,270)
    tmp=np.transpose(tmp, (1,2,0))                         #(90,270,50)
    tmp1=list(zip(*tmp))[::-1]      #type is <class 'zip'> --> <class 'list'>
    tmp1=np.asarray(tmp1)           #type <class 'numpy.ndarray'>, shape (270,90,50)
    tmp1=np.transpose(tmp1,[2,0,1]) #(50,270,90)
    a[:,0:3*nx,3*nx:4*nx]=tmp1

    return a


# rotate faces
# translated from /home/atnguyen/llc270/global/matlab/simple_ctd/MITprof_toolbox/sym_g_mod.m
def sym_g_mod(field_in, sym_in):
    field_out = field_in
    for icur in range(sym_in-4):
        field_out = np.flip(np.transpose(field_out, (0, 2, 1)), axis=2)

    return field_out


### worldmap view --> 5 faces ###
# translated from /home/atnguyen/matlab/atn_tools/patchface3D.m

def patchface3D_wrld_to_5f(array_in):

    nz, ny, nx = np.shape(array_in)
    nx = int(nx/4)
    faces = dict()
    
    # face 1
    faces[1] = array_in[:,:3*nx,:nx]
    
    # face 2
    faces[2] = array_in[:,:3*nx,nx:2*nx]
    
    # face 4
    face4 = array_in[:,:3*nx,2*nx:3*nx]
    faces[4] = sym_g_mod(face4, 5)
    
    # face 5
    face5 = array_in[:,:3*nx,3*nx:4*nx]
    faces[5] = sym_g_mod(face5, 5)
    
    # face 3
    face3 = array_in[:,3*nx:4*nx,:nx]
    faces[3] = sym_g_mod(face3, 7)

    return faces
    