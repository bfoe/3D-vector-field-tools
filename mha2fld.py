#
# reads vetor fields in mha format and converts to AVS "*.fld" for us in PerGeos
#
#
# this tool expects as input a 3 dimensional vector field
# that is, 3 spacial dimensions each voxel containing a 3 component vector
# where the 3 vector components constitute a fourth dimension of the dataset
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
if '--input' in argDict: MHAfile=argDict['--input']; checkfile(MHAfile)
else: MHAfile=""

if MHAfile == "":    
#intercatively choose input MHA file
    MHAfile = askopenfilename(title="Choose MHA file", filetypes=[("MHA files","mha")])
    if MHAfile == "": print ('ERROR: No MHA input file specified'); sys.exit(2)
    MHAfile = os.path.abspath(MHAfile) 
    TKwindows.update()
    try: win32gui.SetForegroundWindow(win32console.GetConsoleWindow())
    except: pass #silent
MHAfile = os.path.abspath(MHAfile)
basename = os.path.splitext(os.path.basename(MHAfile))[0]
dirname  = os.path.dirname(MHAfile)     


'''
read MHA with ITK 

enable the above import lines for this to work
  import new # required for ITK work with pyinstaller
  import itk
  
  
#ITK code: read MHA
image = itk.imread(str(MHAfile)); image.Update()
data = itk.GetArrayFromImage(image)
print (data[15,15,15,0]) #8.46477e+6
SpatResol1 = image.GetSpacing()[0]
SpatResol2 = image.GetSpacing()[1]
SpatResol3 = image.GetSpacing()[2]
'''


''' pure python MHA read ---start--- '''
#read MHA header 
end_header=False
header_dict = {}
with open(MHAfile, "rb") as f:
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
except: print ('ERROR: Parameter "ObjectType" not found in MHA header'); sys.exit(2);
if objecttype !='Image': print ('ERROR: ObjectType must be "Image"'); sys.exit(2);
try: ndim = header_dict["NDims"]
except: print ('ERROR: Parameter "NDims" not found in MHA header'); sys.exit(2);
if ndim !=3: print ('ERROR: Parameter "NDims"<>3 not implemented'); sys.exit(2);
try: binarydata = header_dict["BinaryData"]
except: print ('ERROR: Parameter "BinaryData" not found in MHA header'); sys.exit(2);
if binarydata !='True': print ('ERROR: only format with BinaryData implemented'); sys.exit(2);
try: order = header_dict["BinaryDataByteOrderMSB"]
except: print ('Warning: Parameter "BinaryDataByteOrderMSB" not found assuming "False"'); order='False'
if order !='False': print ('ERROR: only format with BinaryDataByteOrderMSB=Flase implemented'); sys.exit(2);
try: compressed = header_dict["CompressedData"]
except: print ('Warning: Parameter "CompressedData" not found assuming "False"'); compressed='False'
if compressed =='True': compressed=True
else: compressed=False
try: Resolution = header_dict["ElementSpacing"]
except: print ('ERROR: Parameter "ElementSpacing" not found in MHA header'); sys.exit(2);
try:
    Resolution  = Resolution.split()
    SpatResol1 = float (Resolution[0])
    SpatResol2 = float (Resolution[1])
    SpatResol3 = float (Resolution[2])
except: print ('ERROR: Problem parsing parameter "ElementSpacing"'); sys.exit(2);
try: dims = header_dict["DimSize"]
except: print ('ERROR: Parameter "DimSize" not found in MHA header'); sys.exit(2);
try:
    dims  = dims.split()
    dim1 = int (dims[0])
    dim2 = int (dims[1])
    dim3 = int (dims[2])
except: print ('ERROR: Problem parsing parameter "DimSize"'); sys.exit(2);
try: veclen = header_dict["ElementNumberOfChannels"]
except: print ('ERROR: Parameter "ElementNumberOfChannels" not found in MHA header'); sys.exit(2);
if veclen !=3: print ('ERROR: Parameter "ElementNumberOfChannels"<>3 not implemented'); sys.exit(2);
try: datatype = header_dict["ElementType"]
except: print ('ERROR: Parameter "ElementType" not found in MHA header'); sys.exit(2);
if datatype !='MET_FLOAT': print ('ERROR: ElementType must be "MET_FLOAT"'); sys.exit(2);
try: datalocation = header_dict["ElementDataFile"]
except: print ('ERROR: Parameter "ElementDataFile" not found in MHA header'); sys.exit(2);
if datalocation !='LOCAL': print ('ERROR: Parameter "ElementDataFile" must be "LOCAL"'); sys.exit(2);
print('.', end='') #progress indicator
# paramters that are ignored: TransformMatrix, Offset, CenterOfRotation, AnatomicalOrientation, CompressedDataSize

#decode binary string to floats
if compressed: rawdata = zlib.decompress(rawdata); print('.', end='') #progress indicator
if (len(rawdata) % 4) > 0:
    print ("Warning: Data length not a multiple of 4, truncating ....")
    length = int(len(rawdata)/4.0)*4
    rawdata = rawdata[0:length]
if (len(rawdata)) > dim1*dim2*dim3*veclen*4:
    print ("Warning: Data length larger than expected, truncating ....")
    rawdata = rawdata[0:int(dim1*dim2*dim3*veclen*4)]    
if (len(rawdata)) < dim1*dim2*dim3*veclen*4:
    print ("ERROR: Data length less than expected")
    sys.exit(2)
data = np.fromstring (rawdata, dtype=np.float32)
print('.', end='') #progress indicator    
data = data.reshape(dim3,dim2,dim1,veclen)
print('.', end='') #progress indicator
''' pure python MHA read ---end--- '''

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
max_ext1 = (dim1-1)*SpatResol1/2.
max_ext2 = (dim2-1)*SpatResol2/2.
max_ext3 = (dim3-1)*SpatResol3/2.
min_ext1 = -1.0* max_ext1
min_ext2 = -1.0* max_ext2
min_ext3 = -1.0* max_ext3

#write FLD header and data
FLDname = os.path.join(dirname,basename+".fld")
try:
  with open(FLDname, "wb") as f:
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
    print('.', end='') #progress indicator
    data = np.transpose(data, axes = (2,1,0,3))
    data [:,:,:,:] = data [:,:,:,::-1]
    print('.', end='') #progress indicator    
    data = np.ndarray.flatten(data)
    print('.', end='') #progress indicator    
    data.astype('>f').tofile(f)
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