#
# reads "*.txt" vector field files created as regular grid by ComSol
# and converts to "*.mha" format
#
# this tool expects as input a textfile with 6 columns: X, Y, Z, V(x), V(y), V(z)
# where X,Y,Z must be equally spaced (not the mesh coordinates)
#
#
# ----- VERSION HISTORY -----
#
# Version 0.1 - 05, July 2018
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
if '--input' in argDict: INfile=argDict['--input']; checkfile(INfile)
else: INfile=""

if INfile == "":    
#intercatively choose input FID file
    INfile = askopenfilename(title="Choose ComSol txt file", filetypes=[("ComSol txt files",".txt")])
    if INfile == "": print ('ERROR: No input file specified'); sys.exit(2)
    INfile = os.path.abspath(INfile) 
    TKwindows.update()
    try: win32gui.SetForegroundWindow(win32console.GetConsoleWindow())
    except: pass #silent
INfile = os.path.abspath(INfile)
basename = os.path.splitext(os.path.basename(INfile))[0]
dirname  = os.path.dirname(INfile)     

#read raw data
data = np.genfromtxt (INfile, dtype = np.float32, comments='%')
if data.shape[1] != 6: 
    print ('ERROR: Text files is expected to contain 6 columns'); 
    sys.exit(2)
dim1 = np.unique(data [:,0]).shape[0]
dim2 = np.unique(data [:,1]).shape[0]
dim3 = np.unique(data [:,2]).shape[0]
if data.shape[0] != dim1*dim2*dim3: 
    print ('ERROR: Problem figuring out ordering of lines in input textfile');
    print ('       maybe this is not a regularly spaced grid but a mesh ???');    
    sys.exit(2)
Resolution1 = (np.max(data [:,0])-np.min(data [:,0]))/(dim1-1)
Resolution2 = (np.max(data [:,1])-np.min(data [:,1]))/(dim2-1)
Resolution3 = (np.max(data [:,2])-np.min(data [:,2]))/(dim3-1)
offset1 = (np.max(data [:,0])+np.min(data [:,0]))/2
offset2 = (np.max(data [:,1])+np.min(data [:,1]))/2
offset3 = (np.max(data [:,2])+np.min(data [:,2]))/2
#reshape raw data
data = np.reshape (data[:,3:6], (dim1,dim2,dim3,3))
data = np.nan_to_num (data)

print ("dimension  = ",dim1, dim2, dim3)
print ("resolution = ",Resolution1, Resolution2, Resolution3)
print ("offset     = ",offset1, offset2, offset3)
Resolution3 = 2*Resolution2 #quickfix - check
offset3 = 2*offset2         #quickfix - check
print ("resolution corrected = ",Resolution1, Resolution2, Resolution3)
print ("offset     corrected = ",offset1, offset2, offset3)


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