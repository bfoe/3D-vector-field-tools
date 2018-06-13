#
# reads AVS "*.fld" vector field files created by PerGEOS
# and converts to "*.mha" format
#
# this tool expects as input a 3 dimensional vector field
# that is, 3 spacial dimensions each voxel containing a 3 component vector
# where the 3 vector components constitute a fourth dimension of the dataset
#
# The FLD input file is supposed to contain velocity vectors in micrometer/s unit
# this is beenig converted to cm/s in the MHA output file
#
#
# ----- VERSION HISTORY -----
#
# Version 0.1 - 12, June 2018
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
#import nibabel as nib
#import new # required for ITK work with pyinstaller
#import itk

TK_installed=True
try: from tkFileDialog import askopenfilename # Python 2
except: 
    try: from tkinter.filedialog import askopenfilename; # Python3
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
    sys.exit(2)

def checkfile(file): # generic check if file exists
    if not os.path.isfile(file): 
        print ('ERROR:  File not found:\n        '+file); exit(1)

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

def float_to_hex(f):
    result = hex(struct.unpack('<I', struct.pack('<f', f))[0])
    result = result [2:] #del leading "0x"
    if result[-1] == 'L': result = result[0: len(result)-1]
    return result
    
def floatarray_to_hex(f):
    resultstring = ""
    f = np.ndarray.flatten(f)
    for i in range(f.shape[0]):
        resultstring += float_to_hex(f[i])+' '       
    return resultstring

def ITK_Image_SetDirection(itkImage,matrix):
    for i in range(3):
        for j in range(3):
            if j == 0:
                col_idx = 1
            if j == 1:
                col_idx = 0
            if j == 2:
                col_idx = 2             
            itkImage.GetDirection().GetVnlMatrix().set(i,j,matrix[i,col_idx])

    
def usage():
    print ('')
    print ('Usage: '+Program_name+' [options] --input=<inputfile>')
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
try: opts, args =  getopt( sys.argv[1:],'h',['help','version','input='])
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
if '--input' in argDict: FLDfile=argDict['--input']; checkfile(FLDfile)
else: FLDfile=""

if FLDfile == "":    
#intercatively choose input FID file
    FLDfile = askopenfilename(title="Choose AVS fld file", filetypes=[("FLD files","fld")])
    if FLDfile == "": print ('ERROR: No FLD input file specified'); sys.exit(2)
    FLDfile = os.path.abspath(FLDfile) 
    TKwindows.update()
    try: win32gui.SetForegroundWindow(win32console.GetConsoleWindow())
    except: pass #silent
FLDfile = os.path.abspath(FLDfile)
basename = os.path.splitext(os.path.basename(FLDfile))[0]
dirname  = os.path.dirname(FLDfile)     
       
#read fld header 
end_header=False
header_dict = {}
with open(FLDfile, "r") as f:
    while not end_header:
        line = f.readline()    
        if ord(line[0])==12 and ord(line[1])==12: end_header=True 
        if not end_header: 
            if not line.startswith('#'):
                (param_name, current_line) = line.split('=') #split at "="
                value = ParseSingleValue(current_line)
                header_dict[param_name] = value
                
#extract relevant parameters from header and check for not implemented stuff
try: ndim = header_dict["ndim"]
except: print ('ERROR: Parameter "ndim" not found in FLD header'); sys.exit(2);
if ndim !=3: print ('ERROR: Parameter "ndim"<>3 not implemented'); sys.exit(2);
try: dim1 = header_dict["dim1"]
except: print ('ERROR: Parameter "dim1" not found in FLD header'); sys.exit(2);
try: dim2 = header_dict["dim2"]
except: print ('ERROR: Parameter "dim2" not found in FLD header'); sys.exit(2);
try: dim3 = header_dict["dim3"]
except: print ('ERROR: Parameter "dim3" not found in FLD header'); sys.exit(2);
try: nspace = header_dict["nspace"]
except: print ('ERROR: Parameter "nspace" not found in FLD header'); sys.exit(2);
if nspace !=3: print ('ERROR: Parameter "nspace"<>3 not implemented'); sys.exit(2);
try: veclen = header_dict["veclen"]
except: print ('ERROR: Parameter "veclen" not found in FLD header'); sys.exit(2);
if veclen !=3: print ('ERROR: Parameter "veclen"<>3 not implemented'); sys.exit(2);
try: data = header_dict["data"]
except: print ('ERROR: Parameter "data" not found in FLD header'); sys.exit(2);
if data != 'float': print ('ERROR: Data types other than float not implemented'); sys.exit(2);
try: field = header_dict["field"]
except: print ('ERROR: Parameter "field" not found in FLD header'); sys.exit(2);
if field != 'uniform': print ('ERROR: Field types other than uniform not implemented'); sys.exit(2);
try: min_ext = header_dict["min_ext"]
except: print ('ERROR: Parameter "min_ext" not found in FLD header'); sys.exit(2);
try: max_ext = header_dict["max_ext"]
except: print ('ERROR: Parameter "max_ext" not found in FLD header'); sys.exit(2);
min_ext = min_ext.split()
max_ext = max_ext.split()
try:
   Resolution1=(float(max_ext[0])-float(min_ext[0]))/(dim1-1)
   Resolution2=(float(max_ext[1])-float(min_ext[1]))/(dim2-1)
   Resolution3=(float(max_ext[2])-float(min_ext[2]))/(dim3-1)
except: print ('ERROR: while calculating spatial resolution'); sys.exit(2);   
print('.', end='') #progress indicator
           
#read fld data as uint8 (unsigned short)
#find data start (header ends with hex 0C0C)
with open(FLDfile, "rb") as f: FLDrawdata= np.fromfile(f, dtype=np.uint8)
print('.', end='') #progress indicator
zeroCs=np.asarray(np.where(FLDrawdata==12))[0,:] # find hex 0C positions
pairs =np.asarray(np.where(np.diff(zeroCs) == 1)) # find positions of 0C pairs
data_start = zeroCs[pairs[0][0]] # find position of first 0C pair
data_start += 2 # discard the two 0C's +1
try: 
    footer_uint8 = FLDrawdata [data_start+(dim1*dim2*dim3*veclen)*4:FLDrawdata.shape[0]]
    footer_hexstring = ''.join('{:02x}'.format(x) for x in footer_uint8)
except: pass # silent
FLDrawdata = 0 # free memory
zeroCs = 0 # free memory
print('.', end='') #progress indicator

#read fld data as float32
f = open(FLDfile, "rb")
f.seek(data_start, os.SEEK_SET)
data = np.fromfile(f, dtype='>f') # read floats as big endian
try: footer_float = data [dim1*dim2*dim3*veclen:data.shape[0]]
except: pass # silent
try: data = data [0:dim1*dim2*dim3*veclen]
except: print ('ERROR: dimension problem in FLD data'); sys.exit(2); 
data = data.reshape(dim3,dim2,dim1,veclen)
data /= 10000.0 #conversion from micrometer/s to cm/s 

'''
The FLD file has some extra data at the end
to print this in several different formats
enable the code below

print (footer_uint8)
print (footer_hexstring)
print (footer_float)
print (floatarray_to_hex(footer_float))
'''



'''
write NIFTI's with Nibabel
re-read NIFTI's with ITK and write MHA 

enable the above import lines for this to work
  import nibabel as nib
  import new # required for ITK work with pyinstaller
  import itk

#calc magnitude
data_mag = np.sqrt(np.sum(np.square(data), axis=(3)))  
#create NIFTI's
aff = np.eye(4)
aff[0,0] = Resolution3; aff[0,3] = -(data.shape[0]/2)*aff[0,0]
aff[1,1] = Resolution2; aff[1,3] = -(data.shape[1]/2)*aff[1,1]
aff[2,2] = Resolution1; aff[2,3] = -(data.shape[2]/2)*aff[2,2]
#write Phase flow X
NIFTIimg = nib.Nifti1Image(data[:,:,:,2], aff)
try: nib.save(NIFTIimg, os.path.join(dirname,basename+"_X.nii.gz"))
except: print ('\nERROR:  problem while writing results'); sys.exit(1)
#write Phase flow Y
NIFTIimg = nib.Nifti1Image(data[:,:,:,1], aff)
try: nib.save(NIFTIimg, os.path.join(dirname,basename+"_Y.nii.gz"))
except: print ('\nERROR:  problem while writing results'); sys.exit(1)
#write Phase flow Z
NIFTIimg = nib.Nifti1Image(data[:,:,:,0], aff)
try: nib.save(NIFTIimg, os.path.join(dirname,basename+"_Z.nii.gz"))
except: print ('\nERROR:  problem while writing results'); sys.exit(1)
#write Phase flow magnitude
NIFTIimg = nib.Nifti1Image(data_mag[:,:,:], aff)
try: nib.save(NIFTIimg, os.path.join(dirname,basename+"_MAG.nii.gz"))
except: print ('\nERROR:  problem while writing results'); sys.exit(1)

#ITK code: read NIFTI's again
image_X = itk.imread(str(os.path.join(dirname,basename+"_X.nii.gz"))); image_X.Update()
image_Y = itk.imread(str(os.path.join(dirname,basename+"_Y.nii.gz"))); image_Y.Update()
image_Z = itk.imread(str(os.path.join(dirname,basename+"_Z.nii.gz"))); image_Y.Update()

#ITK code: compose vector datacomposer = itk.ComposeImageFilter[itk.Image.F3, itk.Image.VF33].New()
composer = itk.ComposeImageFilter[itk.Image.F3, itk.Image.VF33].New()
composer.SetInput(0, image_X)
composer.SetInput(1, image_Y)
composer.SetInput(2, image_Z)
composer.Update()

#ITK code: write MHA file
writer = itk.ImageFileWriter[itk.Image.VF33].New(composer.GetOutput())
writer.SetFileName(str(os.path.join(dirname,basename+".mha")))
writer.UseCompressionOn ()
writer.Update()

sys.exit(0)
'''



'''
write MHA with pure ITK (nibabel not required)

enable the above import lines for this to work
  import new # required for ITK work with pyinstaller
  import itk
  
  
#create itk image from scratch
data = np.transpose(data, axes = (2,1,0,3))
data [:,:,:,:] = data [:,:,:,::-1]
X=np.zeros(shape=(data.shape[0],data.shape[1],data.shape[2]),dtype=np.float32)
Y=np.zeros(shape=(data.shape[0],data.shape[1],data.shape[2]),dtype=np.float32)
Z=np.zeros(shape=(data.shape[0],data.shape[1],data.shape[2]),dtype=np.float32)
X[:,:,:]=data[:,:,:,0]
Y[:,:,:]=data[:,:,:,1]
Z[:,:,:]=data[:,:,:,2]
image_X = itk.GetImageFromArray(X)
image_Y = itk.GetImageFromArray(Y)
image_Z = itk.GetImageFromArray(Z)
image_X.SetSpacing([Resolution3,Resolution2,Resolution1])
image_Y.SetSpacing([Resolution3,Resolution2,Resolution1])
image_Z.SetSpacing([Resolution3,Resolution2,Resolution1])
image_X.SetOrigin([(dim3/2)*Resolution3,(dim2/2)*Resolution2,-(dim1/2)*Resolution1])
image_Y.SetOrigin([(dim3/2)*Resolution3,(dim2/2)*Resolution2,-(dim1/2)*Resolution1])
image_Z.SetOrigin([(dim3/2)*Resolution3,(dim2/2)*Resolution2,-(dim1/2)*Resolution1])
matrix = np.array([[0,-1,0],[-1,0,0],[0,0,1]]).astype(np.float)
ITK_Image_SetDirection(image_X,matrix) 
ITK_Image_SetDirection(image_Y,matrix)
ITK_Image_SetDirection(image_Z,matrix)

#ITK code: compose vector datacomposer = itk.ComposeImageFilter[itk.Image.F3, itk.Image.VF33].New()
composer = itk.ComposeImageFilter[itk.Image.F3, itk.Image.VF33].New()
composer.SetInput(0, image_X)
composer.SetInput(1, image_Y)
composer.SetInput(2, image_Z)
composer.Update()

#ITK code: write MHA file
writer = itk.ImageFileWriter[itk.Image.VF33].New(composer.GetOutput())
writer.SetFileName(str(os.path.join(dirname,basename+".mha")))
writer.UseCompressionOn ()
writer.Update()

sys.exit(0)
'''

#write MHA (no special libraries required)
ndim   = len(data.shape)-1
TransformMatrix = "-1 0 0 0 -1 0 0 0 1" # negative values for compatibility with nibabel/ITK
offset1=-(dim1/2)*Resolution1
offset2=(dim2/2)*Resolution2 # not negative as consequence of the above TransformMatrix
offset3=(dim3/2)*Resolution3 # not negative as consequence of the above TransformMatrix
FLDname = os.path.join(dirname,basename+".mha")
print('.', end='') #progress indicator
data = np.transpose(data, axes = (2,1,0,3))
data [:,:,:,:] = data [:,:,:,::-1]
print('.', end='') #progress indicator
data = np.ndarray.flatten(data)
print('.', end='') #progress indicator
data = data.newbyteorder('S').astype('>f')
data = bytearray (data)
data = np.asarray(data).astype(np.uint8)
data = data.tostring()
print('.', end='') #progress indicator
compressed = False
data = zlib.compress(data);compressed = True # comment this line 4 uncompressed MHA file
print('.', end='') #progress indicator
data_size=len (data)
try:
  with open(FLDname, "wb") as f:
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
    f.write('ElementSpacing ='+str(Resolution3)+' '+str(Resolution2)+' '+str(Resolution1)+'\n')  
    f.write('DimSize = '+str(int(dim3))+' '+str(int(dim2))+' '+str(int(dim1))+'\n')
    f.write('ElementNumberOfChannels = '+str(int(ndim))+'\n')
    f.write('ElementType = MET_FLOAT\n')     
    f.write('ElementDataFile = LOCAL\n')  
    f.write (data)    
except:
    print ('\nERROR:  problem while writing results'); sys.exit(1)
print ('\nSuccessfully written output file')       
    
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