#
# compares two 3D vector fields in MHA format
# and returns two similarity measures in NIFTI format:
# 1) difference of normalized magnitude values
#    first, magnitude values of bos samples are normalized 
#    with respect to the mean velocity over the whole volume (incl. zeros)
#    then, the difference is calculated for each voxel as (A-B)/((A+B)/2)*100
#    output is in % (0..100)
# 2) difference of directionality 
#    first, vectors are normalized to unit vectors (dividing by their magnitude)
#    then the arccos of the dot product is calculated and converted from rad to angles
#    output is in degrees (0..180)
#
# ----- VERSION HISTORY -----
#
# Version 0.1 - 03, July 2018
#       - 1st public github Release
#
# ----- LICENSE -----                 
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#    For more detail see the GNU General Public License.
#    <http://www.gnu.org/licenses/>.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#    THE SOFTWARE.
#
# ----- REQUIREMENTS ----- 
#
#    This program was developed under Python Version 2.7
#    with the following additional libraries: 
#    - numpy
#    - nibabel
#

from __future__ import print_function
try: import win32gui, win32console
except: pass #silent
import sys
import os
import struct
import zlib
from getopt import getopt
import numpy as np
import nibabel as nib



TK_installed=True
try: 
    from tkFileDialog import askopenfilename # Python 2
    from tkFileDialog import asksaveasfile   # Python 2
    from tkMessageBox import showwarning     # Python 2
    from tkMessageBox import showerror       # Python 2
    from tkMessageBox import showinfo        # Python 2
except: 
    try: from tkinter.filedialog import askopenfilename; # Python3
    except: TK_installed=False
    try: from tkinter.filedialog import asksaveasfile;   # Python3
    except: TK_installed=False
    try: from tkinter.messagebox import showwarning;     # Python3
    except: TK_installed=False    
    try: from tkinter.messagebox import showerror;       # Python3
    except: TK_installed=False       
    try: from tkinter.messagebox import showinfo;        # Python3
    except: TK_installed=False   
try: import Tkinter as tk; # Python2
except: 
    try: import tkinter as tk; # Python3
    except: TK_installed=False
if not TK_installed:
    print ('ERROR: tkinter not installed')
    print ('       on Linux try "yum install tkinter"')
    print ('       on MacOS install ActiveTcl from:')
    print ('       http://www.activestate.com/activetcl/downloads')
    sys.stdout.write('\a\a\a'); sys.stdout.flush() # beep 3x
    sys.exit(2)

def checkfile(file): # generic check if file exists
    if not os.path.isfile(file):
        showerror('ERROR reading file', 'File not found ... operation aborted'); sys.exit(1)    

def ParseSingleValue(val):
    try: # check if int
        result = int(val)
    except ValueError:
        try: # then check if float
            result = float(val)
        except ValueError:
            # if not, should  be string. Remove  newline character.
            result = val.rstrip('\n')
    return result
    
def usage():
    print ('')
    print ('Usage: '+Program_name+' [options] --input1=<inputfile1> --input2=<inputfile2>')
    print ('')
    print ('   Available options are:')
    print ('       --version     : version information')
    print ('       -h --help     : this page')    
    print ('')        
       
#general initialization stuff  
space=' '; slash='/'; 
if sys.platform=="win32": slash='\\' # not really needed, but looks nicer ;)
Program_name = os.path.basename(sys.argv[0]); 
if Program_name.find('.')>0: Program_name = Program_name[:Program_name.find('.')]
Program_version = "v0.1" # program version
python_version=str(sys.version_info[0])+'.'+str(sys.version_info[1])+'.'+str(sys.version_info[2])
# sys.platform = [linux2, win32, cygwin, darwin, os2, os2emx, riscos, atheos, freebsd7, freebsd8]
if sys.platform=="win32": os.system("title "+Program_name)
    
#TK initialization       
TKwindows = tk.Tk(); TKwindows.withdraw() #hiding tkinter window
TKwindows.update()
# the following tries to disable showing hidden files/folders under linux
try: TKwindows.tk.call('tk_getOpenFile', '-foobarz')
except: pass
try: TKwindows.tk.call('namespace', 'import', '::tk::dialog::file::')
except: pass
try: TKwindows.tk.call('set', '::tk::dialog::file::showHiddenBtn', '1')
except: pass
try: TKwindows.tk.call('set', '::tk::dialog::file::showHiddenVar', '0')
except: pass
TKwindows.update()

# parse commandline parameters (if present)
try: opts, args =  getopt( sys.argv[1:],'h',['help','version','input1=','input2='])
except:
    error=str(sys.argv[1:]).replace("[","").replace("]","")
    if "-" in str(error) and not "--" in str(error): 
          print ('ERROR: Commandline '+str(error)+',   maybe you mean "--"')
    else: print ('ERROR: Commandline '+str(error))
    usage(); exit(2)
if len(args)>0: 
    print ('ERROR: Commandline option "'+args[0]+'" not recognized')
    usage(); exit(2)  
argDict = dict(opts)
if '-h' in argDict: usage(); exit(0)   
if '--help' in argDict: usage(); exit(0)  
if '--version' in argDict: print (Program_name+' '+Program_version); exit(0)
if '--input1' in argDict: INfile1=argDict['--input1']; checkfile(INfile1)
else: INfile1=""
if '--input2' in argDict: INfile2=argDict['--input2']; checkfile(INfile2)
else: INfile2=""

if INfile1 == "":    
#intercatively choose input1
    INfile1 = askopenfilename(title="Choose first MHA file", filetypes=[("MHA files","mha")])
    if INfile1 == "": showerror("Open file", "No input file specified ... operation aborted"); sys.exit(2)
    INfile1 = os.path.abspath(INfile1) 
    TKwindows.update()
if INfile2 == "":    
#intercatively choose input1
    INfile2 = askopenfilename(title="Choose second MHA file", filetypes=[("MHA files","mha")])
    if INfile2 == "": showerror("Open file", "No input file specified ... operation aborted"); sys.exit(2)
    INfile2 = os.path.abspath(INfile2) 
    TKwindows.update()    
INfile1 = os.path.abspath(INfile1)
basename1 = os.path.splitext(os.path.basename(INfile1))[0]
basename2 = os.path.splitext(os.path.basename(INfile2))[0]
dirname  = os.path.dirname(INfile1)     

#read MHA header of first input file
end_header=False
header_dict = {}
with open(INfile1, "rb") as f:
    while not end_header:
        line = f.readline()    
        (param_name, current_line) = line.split('=') #split at "=" and strip of spaces
        param_name = param_name.strip()
        current_line = current_line.strip()
        value = ParseSingleValue(current_line)
        header_dict[param_name] = value
        if param_name == 'ElementDataFile': end_header=True
    rawdata = f.read()
    
#extract relevant parameters from header and check for not implemented stuff
try: objecttype = header_dict["ObjectType"]
except: showerror('ERROR parsing MHA', 'Parameter "ObjectType" not found ... operation aborted'); sys.exit(2)
if objecttype !='Image': showerror('ERROR parsing MHA', 'ObjectType must be "Image" ... operation aborted'); sys.exit(2)
try: ndim = header_dict["NDims"]
except: showerror('ERROR parsing MHA', 'Parameter "NDims" not found ... operation aborted'); sys.exit(2)
if ndim !=3: showerror('ERROR parsing MHA', 'Parameter "NDims"<>3 not implemented ... operation aborted'); sys.exit(2)
try: binarydata = header_dict["BinaryData"]
except: showerror('ERROR parsing MHA', 'Parameter "BinaryData" not found ... operation aborted'); sys.exit(2)
if binarydata !='True': showerror('ERROR parsing MHA', 'only format with BinaryData implemented ... operation aborted'); sys.exit(2)
try: order = header_dict["BinaryDataByteOrderMSB"]
except: showwarning('Warning parsing MHA', 'Parameter "BinaryDataByteOrderMSB" not found assuming "False"'); order='False'
if order !='False': showerror('ERROR parsing MHA', 'only format with BinaryDataByteOrderMSB=Flase implemented ... operation aborted'); sys.exit(2)
try: compressed = header_dict["CompressedData"]
except: showwarning('Warning parsing MHA', 'Parameter "CompressedData" not found assuming "False"'); compressed='False'
if compressed =='True': compressed=True
else: compressed=False
try: Resolution = header_dict["ElementSpacing"]
except: showerror('ERROR parsing MHA', 'Parameter "ElementSpacing" not found ... operation aborted'); sys.exit(2)
try:
    Resolution  = Resolution.split()
    SpatResol1 = float (Resolution[0])
    SpatResol2 = float (Resolution[1])
    SpatResol3 = float (Resolution[2])
except: showerror('ERROR parsing MHA', 'Problem parsing parameter "ElementSpacing" ... operation aborted'); sys.exit(2)
try: dims = header_dict["DimSize"]
except: showerror('ERROR parsing MHA', 'Parameter "DimSize" not found ... operation aborted'); sys.exit(2)
try:
    dims  = dims.split()
    dim1 = int (dims[0])
    dim2 = int (dims[1])
    dim3 = int (dims[2])
except: showerror('ERROR parsing MHA', 'Problem parsing parameter "DimSize" ... operation aborted'); sys.exit(2)
try: veclen = header_dict["ElementNumberOfChannels"]
except: showerror('ERROR parsing MHA', 'Parameter "ElementNumberOfChannels" not found ... operation aborted'); sys.exit(2)
if veclen !=3: showerror('ERROR parsing MHA', 'Parameter "ElementNumberOfChannels"<>3 not implemented ... operation aborted'); sys.exit(2) 
try: datatype = header_dict["ElementType"]
except: showerror('ERROR parsing MHA', 'Parameter "ElementType" not found ... operation aborted'); sys.exit(2)
if datatype !='MET_FLOAT': showerror('ERROR parsing MHA', 'Parameter "ElementType" must be "MET_FLOAT" ... operation aborted'); sys.exit(2)
try: datalocation = header_dict["ElementDataFile"]
except: showerror('ERROR parsing MHA', 'Parameter "ElementDataFile" not found ... operation aborted'); sys.exit(2)
if datalocation !='LOCAL': showerror('ERROR parsing MHA', 'Parameter "ElementDataFile" must be "LOCAL" ... operation aborted'); sys.exit(2)
# paramters that are ignored: TransformMatrix, Offset, CenterOfRotation, AnatomicalOrientation, CompressedDataSize

#decode binary string to floats
if compressed: rawdata = zlib.decompress(rawdata); 
if (len(rawdata) % 4) > 0:
    showwarning('Warning reading MHA', 'Data length not a multiple of 4 ... truncating')
    length = int(len(rawdata)/4.0)*4
    rawdata = rawdata[0:length]
if (len(rawdata)) > dim1*dim2*dim3*veclen*4:
    showwarning('Warning reading MHA', 'Data length larger than expected ... truncating')
    rawdata = rawdata[0:int(dim1*dim2*dim3*veclen*4)]    
if (len(rawdata)) < dim1*dim2*dim3*veclen*4:
    showerror('ERROR reading MHA', 'Data length less than expected ... operation aborted'); sys.exit(2)
    sys.exit(2)
data1 = np.fromstring (rawdata, dtype=np.float32)
data1 = data1.reshape(dim3,dim2,dim1,veclen)

#read MHA header of second input file
end_header=False
header_dict = {}
with open(INfile2, "rb") as f:
    while not end_header:
        line = f.readline()    
        (param_name, current_line) = line.split('=') #split at "=" and strip of spaces
        param_name = param_name.strip()
        current_line = current_line.strip()
        value = ParseSingleValue(current_line)
        header_dict[param_name] = value
        if param_name == 'ElementDataFile': end_header=True
    rawdata = f.read()
    
#extract relevant parameters from header and check for not implemented stuff
try: objecttype = header_dict["ObjectType"]
except: showerror('ERROR parsing MHA', 'Parameter "ObjectType" not found ... operation aborted'); sys.exit(2)
if objecttype !='Image': showerror('ERROR parsing MHA', 'ObjectType must be "Image" ... operation aborted'); sys.exit(2)
try: ndim = header_dict["NDims"]
except: showerror('ERROR parsing MHA', 'Parameter "NDims" not found ... operation aborted'); sys.exit(2)
if ndim !=3: showerror('ERROR parsing MHA', 'Parameter "NDims"<>3 not implemented ... operation aborted'); sys.exit(2)
try: binarydata = header_dict["BinaryData"]
except: showerror('ERROR parsing MHA', 'Parameter "BinaryData" not found ... operation aborted'); sys.exit(2)
if binarydata !='True': showerror('ERROR parsing MHA', 'only format with BinaryData implemented ... operation aborted'); sys.exit(2)
try: order = header_dict["BinaryDataByteOrderMSB"]
except: showwarning('Warning parsing MHA', 'Parameter "BinaryDataByteOrderMSB" not found assuming "False"'); order='False'
if order !='False': showerror('ERROR parsing MHA', 'only format with BinaryDataByteOrderMSB=Flase implemented ... operation aborted'); sys.exit(2)
try: compressed = header_dict["CompressedData"]
except: showwarning('Warning parsing MHA', 'Parameter "CompressedData" not found assuming "False"'); compressed='False'
if compressed =='True': compressed=True
else: compressed=False
try: Resolution = header_dict["ElementSpacing"]
except: showerror('ERROR parsing MHA', 'Parameter "ElementSpacing" not found ... operation aborted'); sys.exit(2)
try:
    Resolution  = Resolution.split()
    SpatResol1 = float (Resolution[0])
    SpatResol2 = float (Resolution[1])
    SpatResol3 = float (Resolution[2])
except: showerror('ERROR parsing MHA', 'Problem parsing parameter "ElementSpacing" ... operation aborted'); sys.exit(2)
try: dims = header_dict["DimSize"]
except: showerror('ERROR parsing MHA', 'Parameter "DimSize" not found ... operation aborted'); sys.exit(2)
try:
    dims  = dims.split()
    dim1 = int (dims[0])
    dim2 = int (dims[1])
    dim3 = int (dims[2])
except: showerror('ERROR parsing MHA', 'Problem parsing parameter "DimSize" ... operation aborted'); sys.exit(2)
try: veclen = header_dict["ElementNumberOfChannels"]
except: showerror('ERROR parsing MHA', 'Parameter "ElementNumberOfChannels" not found ... operation aborted'); sys.exit(2)
if veclen !=3: showerror('ERROR parsing MHA', 'Parameter "ElementNumberOfChannels"<>3 not implemented ... operation aborted'); sys.exit(2) 
try: datatype = header_dict["ElementType"]
except: showerror('ERROR parsing MHA', 'Parameter "ElementType" not found ... operation aborted'); sys.exit(2)
if datatype !='MET_FLOAT': showerror('ERROR parsing MHA', 'Parameter "ElementType" must be "MET_FLOAT" ... operation aborted'); sys.exit(2)
try: datalocation = header_dict["ElementDataFile"]
except: showerror('ERROR parsing MHA', 'Parameter "ElementDataFile" not found ... operation aborted'); sys.exit(2)
if datalocation !='LOCAL': showerror('ERROR parsing MHA', 'Parameter "ElementDataFile" must be "LOCAL" ... operation aborted'); sys.exit(2)
# paramters that are ignored: TransformMatrix, Offset, CenterOfRotation, AnatomicalOrientation, CompressedDataSize

#decode binary string to floats
if compressed: rawdata = zlib.decompress(rawdata); 
if (len(rawdata) % 4) > 0:
    showwarning('Warning reading MHA', 'Data length not a multiple of 4 ... truncating')
    length = int(len(rawdata)/4.0)*4
    rawdata = rawdata[0:length]
if (len(rawdata)) > dim1*dim2*dim3*veclen*4:
    showwarning('Warning reading MHA', 'Data length larger than expected ... truncating')
    rawdata = rawdata[0:int(dim1*dim2*dim3*veclen*4)]    
if (len(rawdata)) < dim1*dim2*dim3*veclen*4:
    showerror('ERROR reading MHA', 'Data length less than expected ... operation aborted'); sys.exit(2)
    sys.exit(2)
data2 = np.fromstring (rawdata, dtype=np.float32)
data2 = data2.reshape(dim3,dim2,dim1,veclen)

#check if the two datasets are compatible
if data1.shape != data2.shape: showerror('ERROR reading MHAs', 'Input files have different dimensions ... operation aborted'); sys.exit(2)

#calc magnitude, normalize and calculate difference
dim=data1.shape
data1_mag = np.sqrt(np.sum(np.square(data1[:,:,:,:]),axis=3)); nonzero1 = np.nonzero(data1_mag)
data2_mag = np.sqrt(np.sum(np.square(data2[:,:,:,:]),axis=3)); nonzero2 = np.nonzero(data2_mag)
data1_avg = np.average(data1_mag); data2_avg = np.average(data2_mag)

nonzero = np.nonzero(data1_mag+data2_mag)
data_mag_diff = np.zeros(shape=(dim[0],dim[1],dim[2]), dtype=np.float32)
data_mag_diff[nonzero] = (data1_mag[nonzero]/data1_avg - data2_mag[nonzero]/data2_avg) \
                       /((data1_mag[nonzero]/data1_avg + data2_mag[nonzero]/data2_avg)/2.)*100  # result in % 
data_mag_diff[:,:,dim[2]-1]=0 # there's trash in here, dunno why                       

#normalize to unity vectors
dummy=data1[:,:,:,0]; dummy[nonzero1] = np.divide(dummy[nonzero1],data1_mag[nonzero1]); data1[:,:,:,0]=dummy
dummy=data1[:,:,:,1]; dummy[nonzero1] = np.divide(dummy[nonzero1],data1_mag[nonzero1]); data1[:,:,:,1]=dummy
dummy=data1[:,:,:,2]; dummy[nonzero1] = np.divide(dummy[nonzero1],data1_mag[nonzero1]); data1[:,:,:,2]=dummy
dummy=data2[:,:,:,0]; dummy[nonzero2] = np.divide(dummy[nonzero2],data2_mag[nonzero2]); data2[:,:,:,0]=dummy
dummy=data2[:,:,:,1]; dummy[nonzero2] = np.divide(dummy[nonzero2],data2_mag[nonzero2]); data2[:,:,:,1]=dummy
dummy=data2[:,:,:,2]; dummy[nonzero2] = np.divide(dummy[nonzero2],data2_mag[nonzero2]); data2[:,:,:,2]=dummy

#calc difference of directionality
data1 = data1.reshape (dim[0]*dim[1]*dim[2],dim[3])
data2 = data2.reshape (dim[0]*dim[1]*dim[2],dim[3])
data1_mag = data1_mag.reshape (dim[0]*dim[1]*dim[2])
data2_mag = data2_mag.reshape (dim[0]*dim[1]*dim[2])
nonzero = np.nonzero(data1_mag*data2_mag)
cos_angle = np.zeros(shape=(dim[0]*dim[1]*dim[2]), dtype=np.float32)
angle     = np.zeros(shape=(dim[0]*dim[1]*dim[2]), dtype=np.float32)
for i in range (0,dim[0]*dim[1]*dim[2]):
  cos_angle[i] = np.dot(data1[i,:],data2[i,:])
angle[nonzero] = np.arccos(np.clip(cos_angle[nonzero], -1, 1))*180./np.pi # result in angle 0..180
angle = angle.reshape (dim[0],dim[1],dim[2])
angle[:,:,dim[2]-1]=0 # there's trash in here, dunno why

#transform to int
max_magnitude = np.amax(data_mag_diff);
data_mag_diff *= 32767./max_magnitude
data_mag_diff = data_mag_diff.astype(np.int16)
max_angle = np.amax(angle);
angle *= 32767./max_angle
angle = angle.astype(np.int16)


#save NIFTI
aff = np.eye(4)
aff[0,0] = Resolution [0]; aff[0,3] = -(data_mag_diff.shape[0]/2)*aff[0,0]
aff[1,1] = Resolution [1]; aff[1,3] = -(data_mag_diff.shape[1]/2)*aff[1,1]
aff[2,2] = Resolution [2]; aff[2,3] = -(data_mag_diff.shape[2]/2)*aff[2,2]
NIFTIimg_mag = nib.Nifti1Image(data_mag_diff, aff)
NIFTIimg_mag.header.set_slope_inter(max_magnitude/32767.,0)
NIFTIimg_mag.header.set_xyzt_units(3, 8)
NIFTIimg_mag.set_sform(aff, code=0)
NIFTIimg_mag.set_qform(aff, code=1)
NIFTIimg_ang = nib.Nifti1Image(angle, aff)
NIFTIimg_ang.header.set_slope_inter(max_angle/32767.,0)
NIFTIimg_ang.header.set_xyzt_units(3, 8)
NIFTIimg_ang.set_sform(aff, code=0)
NIFTIimg_ang.set_qform(aff, code=1)
OK=True
try: nib.save(NIFTIimg_mag, os.path.join(dirname,basename1+'-'+basename2+'_MAGNT_DIFF.nii.gz'))
except: showerror("Write file", "Unable to write output file ",basename1+'-'+basename2+'_MAGNT_DIFF.nii.gz');OK=False   
try: nib.save(NIFTIimg_ang, os.path.join(dirname,basename1+'-'+basename2+'_ANGLE_DIFF.nii.gz')) 
except: showerror("Write file", "Unable to write output file ",basename1+'-'+basename2+'_ANGLE_DIFF.nii.gz');OK=False  

if OK: showinfo("Done", "Files written successfully")