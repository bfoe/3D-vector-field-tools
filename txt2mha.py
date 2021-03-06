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
import math
import struct
import zlib
from getopt import getopt
import numpy as np


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
    
def round_auto (value):
    digits=int(math.ceil(-math.log10(abs(value))))
    return round(value,digits+6)
    
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

#read header
end_header=False
header_dict = {}
with open(INfile, "r") as f:
    while not end_header:
        line = f.readline()    
        if not line.startswith('%'): end_header=True 
        if not end_header: 
           dummy = map(str.strip, line[1:-1].split(':'))
           if len(dummy) > 1: 
                param_name = dummy[0]
                if len(dummy) > 2: value =  " ".join(dummy[1:-1])
                else: value = dummy[1]
                header_dict[param_name] = value
           else: # no ":" in string
                dummy = map(str.strip, line[1:-1].split())
                if len(dummy) == 9: # extract the velocity units
                   header_dict["Velocity unit X"] = dummy[4].strip('(').strip(')')
                   header_dict["Velocity unit Y"] = dummy[6].strip('(').strip(')')
                   header_dict["Velocity unit Z"] = dummy[8].strip('(').strip(')')
                   
#sanity checks
try: ndim = header_dict["Dimension"]
except: print ('ERROR: Parameter "Dimension" not found in header'); sys.exit(2);
if ndim !="3": print ('ERROR: Parameter "Dimension"<>3 not implemented'); sys.exit(2);
try: expr = header_dict["Expressions"]
except: print ('ERROR: Parameter "Expressions" not found in header'); sys.exit(2);
if expr !="3": print ('ERROR: Parameter "Expressions"<>3 not implemented'); sys.exit(2);
try: nodes = header_dict["Nodes"]
except: print ('ERROR: Parameter "Nodes" not found in header'); sys.exit(2);
try: nodes=int(nodes)                 
except: print ('ERROR: Problem parsing "Nodes" parameter'); sys.exit(2);         
try: l_unit = header_dict["Length unit"]
except: print ('ERROR: Parameter "Length unit" not found in header'); sys.exit(2);
try:
    if l_unit == "m": l_unit=1
    elif l_unit == "dm": l_unit=10
    elif l_unit == "cm": l_unit=100
    elif l_unit == "mm": l_unit=1000
    elif l_unit == str(chr(194))+str(chr(181))+"m": l_unit=1000000 # 194+181 is for micrometer
    else: print ('ERROR: Unknown "Length unit" parameter'); sys.exit(2);
except: print ('ERROR: Problem parsing "Length unit" parameter'); sys.exit(2);
try: 
    v_unit = header_dict["Velocity unit X"]
    v1_unit = header_dict["Velocity unit Y"]
    v2_unit = header_dict["Velocity unit Z"]
except: print ('ERROR: Parameter "Velocity unit" not found in header'); sys.exit(2);
if v_unit != v1_unit or v_unit != v2_unit:
    print ('ERROR: Different Velocity unit for X,Y,Z components not implemented'); sys.exit(2);
try:
    if v_unit == "m/s": v_unit=1
    elif v_unit == "dm/s": v_unit=10
    elif v_unit == "cm/s": v_unit=100
    elif v_unit == "mm/s": v_unit=1000
    elif v_unit == str(chr(194))+str(chr(181))+"m/s": v_unit=1000000# 194+181 is for micrometer
    else: print ('ERROR: Unknown "Velocity unit" parameter'); sys.exit(2);
except: print ('ERROR: Problem parsing "Velocity unit" parameter'); sys.exit(2);
print ("Nodes =", nodes)
print ("Length unit =", l_unit)
print ("Velocity unit =", v_unit)
         
#read raw data
data = np.genfromtxt (INfile, dtype = np.float32, comments='%')
if data.shape[1] != 6: 
    print ('ERROR: Text files is expected to contain 6 columns'); 
    sys.exit(2)
if data.shape[0] != nodes: #santiy check
    print ('Warning: number of data rows different from value specified in header ');
dim1 = np.unique(data [:,0]).shape[0]
dim2 = np.unique(data [:,1]).shape[0]
dim3 = np.unique(data [:,2]).shape[0]
if data.shape[0] != dim1*dim2*dim3: 
    print ('ERROR: Problem figuring out ordering of lines in input textfile');
    print ('       maybe this is not a regularly spaced grid but a mesh ???');    
    sys.exit(2)   
Extension1  = (np.max(data [:,0])-np.min(data [:,0]))/l_unit
Extension2  = (np.max(data [:,1])-np.min(data [:,1]))/l_unit
Extension3  = (np.max(data [:,2])-np.min(data [:,2]))/l_unit
Resolution1 = round_auto(Extension1/(dim1-1))
Resolution2 = round_auto(Extension2/(dim2-1))
Resolution3 = round_auto(Extension3/(dim3-1))
offset1 = (np.max(data [:,0])+np.min(data [:,0]))/2/l_unit
offset2 = (np.max(data [:,1])+np.min(data [:,1]))/2/l_unit
offset3 = (np.max(data [:,2])+np.min(data [:,2]))/2/l_unit
#reshape data
data = np.reshape (data[:,3:6], (dim3,dim2,dim1,3))
data = np.nan_to_num (data)
data /= v_unit
abs_data = np.sqrt(np.sum(np.square(data),axis=3))

print ("Maximum velocity ="+str(np.amax(abs_data))+" m/s")
print ("Data dimension =", dim1, dim2,dim3)
print ("Resolution = "+str(Resolution1)+" m,   "+str(Resolution2)+" m,   "+str(Resolution3)+" m")
print ("Offset = = "+str(offset1)+" m,   "+str(offset2)+" m,   "+str(offset3)+" m")

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