#
# creates a digial phantom for flow simulations
# that consists o a simple cilindrical tube
#
#    This program was developed under Python Version 2.7
#    with the following additional libraries: 
#    - numpy
#    - nibabel
#


from __future__ import print_function
from math import floor
import sys
import os
import math
import zlib
import numpy as np
import nibabel as nib

#read input from keyboard
OK=False
while not OK:
    dummy = raw_input("Enter length [mm]    (default =  20mm): ")
    if dummy == '': dummy=20
    try: length = float(dummy); OK=True
    except: print ("Input Error")
    dummy = raw_input("Enter diameter [mm]  (default = 1.5mm): ")
    if dummy == '': dummy=1.5
    try: diameter = float(dummy); OK=True
    except: print ("Input Error")
    dummy = raw_input("Resolution ["+str(chr(230))+"m]      (default = 100"+str(chr(230))+"m): ")
    if dummy == '': dummy=100
    try: resolution = float(dummy); OK=True
    except: print ("Input Error")
    dummy = raw_input("Pressure [Pa] (default=20000Pa=0.2bar): ")
    if dummy == '': dummy=20000
    try: pressure = float(dummy); OK=True
    except: print ("Input Error")

#convert to meters
length     *= 1.0e-3 # mm to m
diameter   *= 1.0e-3 # mm to m    
resolution *= 1.0e-6 # um to m
    
tube_points_transv = int(diameter/resolution)
tube_points_long   = int(length/resolution)
eps = int(tube_points_transv*0.2)
if eps<4: eps=4
if (tube_points_transv+eps)%2 == 0: eps += 1 # make it odd
dim1 = tube_points_transv+eps
dim2 = tube_points_transv+eps
dim3 = tube_points_long
data = np.zeros (shape=(dim1,dim2,dim3), dtype=np.int16)

for x in range (0,dim1):
  for y in range (0,dim2):
      if np.sqrt(np.square(x-dim1/2) + np.square(y-dim2/2))*resolution <= float(diameter/2.0):
          data[x,y,0] = 1
for z in range (1,dim3):          
    data[:,:,z] = data[:,:,0]

#check areas
nom_area = np.square(float(diameter/2.))*np.pi
eff_area = np.count_nonzero(data[:,:,0])*resolution**2
error    = (eff_area-nom_area)/nom_area*100.
print ('')
print ('Nominal   crossection area : %0.1f' % (nom_area*1.0e6**2.), str(chr(230))+'m'+str(chr(253)))
print ('Effective crossection area : %0.1f' % (eff_area*1.0e6**2.), str(chr(230))+'m'+str(chr(253)))
print ('Error after discretization : %0.2f' % error, '%')    
    

#
# calculation velocities with the Hagen-Poiseuille equation:
# https://en.wikipedia.org/wiki/Hagen%E2%80%93Poiseuille_equation
# https://pt.wikipedia.org/wiki/Lei_de_Poiseuille
#
# velocity = 1/(4*viscosity) * pressure/tube_length *(tube_radius^2 - r^2)
# where "r" distance from cylinder center 
#

viscosity = 0.001 # [Pa*s] water at room temperature

velocity = np.zeros (shape=(dim1,dim2,dim3), dtype=np.float32)
for x in range (0,dim1):
  for y in range (0,dim2):
      r = np.sqrt(np.square(x-dim1/2) + np.square(y-dim2/2))*resolution
      velocity [x,y,0] = 1/(4*viscosity) * pressure/length *((diameter/2.)**2 - r**2)
for z in range (1,dim3):          
    velocity[:,:,z] = velocity[:,:,0]
mask = data [:,:,:] != 0
velocity *= mask

#check flow rates
nom_flow_rate = pressure*np.pi*(diameter/2.)**4/(8*length*viscosity)
eff_flow_rate = np.sum(velocity[:,:,0])*resolution**2
error    = (eff_flow_rate-nom_flow_rate)/nom_flow_rate*100.
print ('Maximum flow velocity      : %0.1f' % (np.amax(velocity[:,:,:])*1.0e2), 'cm/s')
print ('Nominal   flow rate        : %0.3f' % (nom_flow_rate*1.0e6), 'ml')
print ('Effective flow rate        : %0.3f' % (eff_flow_rate*1.0e6), 'ml')
print ('Error after discretization : %0.2f' % error, '%')

# calculation permeability
# https://en.wikipedia.org/wiki/Darcy_(unit)
# https://pt.wikipedia.org/wiki/Lei_de_Darcy
#
# permeability =  flow_rate*length*viscosity/(pressure*area)
# unit is [m^2]
#
nom_permeability = nom_flow_rate*length*viscosity/(pressure*nom_area)
eff_permeability = eff_flow_rate*length*viscosity/(pressure*eff_area)
error    = (eff_permeability-nom_permeability)/nom_permeability*100.
print ('Nominal   permeability     : %0.1f' % (nom_permeability*1.0e6**2), str(chr(230))+'m'+str(chr(253)))
print ('Effective permeability     : %0.1f' % (eff_permeability*1.0e6**2), str(chr(230))+'m'+str(chr(253)))
print ('Error after discretization : %0.2f' % error, '%')

#createNIFTI of binarized Phantom
filename  = 'Pantom_L'+str(int(length*1e3))+'mm_D'+str(diameter*1e3)+'mm_R'
filename += str(int(round(resolution*1e6)))+'um.nii.gz'
aff = np.eye(4)
aff[0,0] = resolution*1.0e6; aff[0,3] = -(data.shape[0]/2)*aff[0,0]
aff[1,1] = resolution*1.0e6; aff[1,3] = -(data.shape[1]/2)*aff[1,1]
aff[2,2] = resolution*1.0e6; aff[2,3] = -(data.shape[2]/2)*aff[2,2]
#write 
NIFTIimg = nib.Nifti1Image(data[:,:,:], aff)
NIFTIimg.header.set_xyzt_units(3, 8)
NIFTIimg.set_sform(aff, code=0)
NIFTIimg.set_qform(aff, code=1)
NIFTIimg.header.set_slope_inter(1,0)
try: nib.save(NIFTIimg, filename)
except: print ('\nERROR:  problem while writing result'); sys.exit(1)
#writesucess    
print ('\nSuccessfully written output file "'+filename+'"') 


#convert velocity to int
vel_int_cm = velocity*100. #velocity in cm/s
vel_max = np.amax (vel_int_cm)    
vel_int_cm = vel_int_cm*32767./vel_max
vel_int_cm = vel_int_cm.astype (np.int16)    
    
#createNIFTI of velocity magnitude
filename  = 'Veloci_L'+str(int(length*1e3))+'mm_D'+str(diameter*1e3)+'mm_R'
filename += str(int(round(resolution*1e6)))+'um_P'+str(int(pressure))+'Pa.nii.gz'
aff = np.eye(4)
aff[0,0] = resolution*1.0e6; aff[0,3] = -(data.shape[0]/2)*aff[0,0]
aff[1,1] = resolution*1.0e6; aff[1,3] = -(data.shape[1]/2)*aff[1,1]
aff[2,2] = resolution*1.0e6; aff[2,3] = -(data.shape[2]/2)*aff[2,2]
#write 
NIFTIimg = nib.Nifti1Image(vel_int_cm[:,:,:], aff)
NIFTIimg.header.set_xyzt_units(3, 8)
NIFTIimg.set_sform(aff, code=0)
NIFTIimg.set_qform(aff, code=1)
NIFTIimg.header.set_slope_inter(vel_max/32767.,0)
try: nib.save(NIFTIimg, filename)
except: print ('ERROR:  problem while writing result'); sys.exit(1)
#writesucess    
print ('Successfully written output file "'+filename+'"')    


data = np.zeros (shape=(dim1,dim2,dim3,3), dtype=np.float32) 
data [:,:,:,0] = velocity*100. # same as NIFTI: convert velocity from m/s to cm/s

#write MHA of velocity vector field
filename  = 'Veloci_L'+str(int(length*1e3))+'mm_D'+str(diameter*1e3)+'mm_R'
filename += str(int(round(resolution*1e6)))+'um_P'+str(int(pressure))+'Pa.mha'
ndim   = len(data.shape)-1
TransformMatrix = "-1 0 0 0 -1 0 0 0 1" # negative values for compatibility with nibabel/ITK
offset1=-(dim1/2)*resolution*1.0e6
offset2=(dim2/2)*resolution*1.0e6 # not negative as consequence of the above TransformMatrix
offset3=(dim3/2)*resolution*1.0e6 # not negative as consequence of the above TransformMatrix
data = np.ndarray.flatten(data)
data = data.newbyteorder('S').astype('>f')
data = bytearray (data)
data = np.asarray(data).astype(np.uint8)
data = data.tostring()
compressed = False
data = zlib.compress(data);compressed = True # comment this line 4 uncompressed MHA file
data_size=len (data)
try:
  with open(filename, "wb") as f:
    f.write('ObjectType = Image\n')
    f.write('NDims='+str(int(ndim))+'\n')
    f.write('BinaryData = True\n')
    f.write('BinaryDataByteOrderMSB = False\n')
    if compressed: 
        f.write('CompressedData = True\n')
        f.write('CompressedDataSize = '+str(data_size)+'\n')        
    else: 
        f.write('CompressedData = False\n')
    f.write('TransformMatrix = '+TransformMatrix+'\n')
    f.write('Offset = '+str(offset3)+' '+str(offset2)+' '+str(offset1)+'\n')    
    f.write('CenterOfRotation = 0 0 0\n')  
    f.write('AnatomicalOrientation = LPI\n')
    f.write('ElementSpacing ='+str(resolution*1.0e6)+' '+str(resolution*1.0e6)+' '+str(resolution*1.0e6)+'\n')  
    f.write('DimSize = '+str(int(dim3))+' '+str(int(dim2))+' '+str(int(dim1))+'\n')
    f.write('ElementNumberOfChannels = '+str(int(ndim))+'\n')
    f.write('ElementType = MET_FLOAT\n')     
    f.write('ElementDataFile = LOCAL\n')  
    f.write (data)    
except:
    print ('ERROR:  problem while writing results'); sys.exit(1)
print ('Successfully written output file "'+filename+'"')      

# conversion from cm/s to micrometer/s
data = np.zeros (shape=(dim1,dim2,dim3,3), dtype=np.float32) 
data [:,:,:,0] = velocity*1.0e6 # same as NIFTI: convert velocity from m/s to um/s

#calculate variables for FLD header
ndim   = len(data.shape)-1
dim1   = data.shape[0]
dim2   = data.shape[1]
dim3   = data.shape[2]
veclen = data.shape[3]
nspace = ndim
data_type = 'float'
field  = 'uniform'
min_ext = ''
max_ext = ''
max_ext1 = (dim1-1)*resolution*1.0e6/2.
max_ext2 = (dim2-1)*resolution*1.0e6/2.
max_ext3 = (dim3-1)*resolution*1.0e6/2.
min_ext1 = -1.0* max_ext1
min_ext2 = -1.0* max_ext2
min_ext3 = -1.0* max_ext3

#write FLD header and data
filename  = 'Veloci_L'+str(int(length*1e3))+'mm_D'+str(diameter*1e3)+'mm_R'
filename += str(int(round(resolution*1e6)))+'um_P'+str(int(pressure))+'Pa.fld'
try:
  with open(filename, "wb") as f:
    f.write('# AVS field file\n')
    f.write('# written for PerGeos\n')
    f.write('#\n')
    f.write('ndim='+str(int(ndim))+'\n')
    f.write('dim1='+str(int(dim1))+'\n')
    f.write('dim2='+str(int(dim2))+'\n')
    f.write('dim3='+str(int(dim3))+'\n')
    f.write('nspace='+str(int(nspace))+'\n')    
    f.write('veclen='+str(int(veclen))+'\n')   
    f.write('data='+data_type+'\n')  
    f.write('field='+field+'\n')
    f.write('min_ext='+str(min_ext1)+' '+str(min_ext2)+' '+str(min_ext3)+'\n')   
    f.write('max_ext='+str(max_ext1)+' '+str(max_ext2)+' '+str(max_ext3)+'\n')
    f.write(chr(12))
    f.write(chr(12))
    data = np.transpose(data, axes = (2,1,0,3))
    data [:,:,:,:] = data [:,:,:,::-1]   
    data = np.ndarray.flatten(data)   
    data.astype('>f').tofile(f)
except:
    print ('\nERROR:  problem while writing results'); sys.exit(1)
print ('Successfully written output file "'+filename+'"')      
    
#end
if sys.platform=="win32": os.system("pause") # windows
else: 
    #os.system('read -s -n 1 -p "Press any key to continue...\n"')
    import termios
    print("Press any key to continue...")
    fd = sys.stdin.fileno()
    oldterm = termios.tcgetattr(fd)
    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)
    try: result = sys.stdin.read(1)
    except IOError: pass
    finally: termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)    


 