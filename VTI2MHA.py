#
# uses ITK to convert whatever format ITK can read and write
#
# supported file formats are described here:
#     https://itk.org/Wiki/ITK/FAQ#What_3D_file_formats_can_ITK_import_and_export.3F
#     https://itk.org/Wiki/ITK/File_Formats
#
# ITK identifies the file format by the file extension
# therefore just specify the output file name and all the rest 
# goes automatically
#
# things that can go wrong:
#     - incompatible file formats
#       for example MHA files can contain several 3D components, e.g. on for 
#       each component of a vector field.
#       opposed to this NIFTI files are not adequate to store vector fields
#     - at this point of time the python ITK wrapper is at version level 4.13.0
#       obviously only file formats supported by the used ITK version are supported    
#
# ----- VERSION HISTORY -----
#
# Version 0.1 - 29, June 2018
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
#    - itk 
#


from __future__ import print_function
import sys
import os
from getopt import getopt
import new # required for ITK work with pyinstaller
import zlib
import numpy as np
from vtk import vtkXMLImageDataReader
from vtk.util import numpy_support


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
if '--input' in argDict: INfile=argDict['--input'];
else: INfile=""



if INfile == "":
    #intercatively choose input file
    INfile = askopenfilename(title="Open file", filetypes=[("VTI files",('*.vti'))])
    if INfile == "": showwarning("Open file", "No input file specified ... operation aborted"); sys.exit(2)
    INfile = os.path.abspath(INfile)
    INfile=str(INfile)     
    
#read file
reader = vtkXMLImageDataReader()
#reader = vtk.vtkMetaImageReader()
#reader = vtk.vtkImageReader()
reader.SetFileName(INfile)
reader.Update()
vtk_data=reader.GetOutput()

#get header parameters
dirname  = os.path.dirname(INfile)
basename = os.path.splitext(os.path.basename(INfile))[0]
ndim = vtk_data.GetDataDimension() # this must be 3
if  ndim != 3: showerror("ERROR", "Only 3D files implemented ... operation aborted"); sys.exit(2)
Resolution1 = vtk_data.GetSpacing()[2]
Resolution2 = vtk_data.GetSpacing()[1]
Resolution3 = vtk_data.GetSpacing()[0]
dim1 = vtk_data.GetDimensions()[2]
dim2 = vtk_data.GetDimensions()[1]
dim3 = vtk_data.GetDimensions()[0]
offset1 = vtk_data.GetOrigin()[2]
offset2 = vtk_data.GetOrigin()[1]
offset3 = vtk_data.GetOrigin()[0]
n_cell_arrays = vtk_data.GetCellData().GetNumberOfArrays() # this must be 0
if  n_cell_arrays != 0: showerror("ERROR", "Unkown file structure ... operation aborted"); sys.exit(2)
narrays = vtk_data.GetPointData().GetNumberOfArrays()

#write mha file (s) one for each component
for i in range(0,narrays):
    arrayname = vtk_data.GetPointData().GetArrayName(i)
    ncomponents = vtk_data.GetPointData().GetAbstractArray(i).GetNumberOfComponents()
    #data = numpy_support.vtk_to_numpy(vtk_data.GetPointData().GetArray(i))
    data = numpy_support.vtk_to_numpy(vtk_data.GetPointData().GetAbstractArray(i))
    data = data.reshape((dim1,dim2,dim3,ncomponents),order="F")
    data = data [:,:,:,::-1]
   
    #write MHA (no special libraries required)
    TransformMatrix = "-1 0 0 0 -1 0 0 0 1" # negative values for compatibility with nibabel/ITK
    offset1 *= -1 # offset negative as consequence of the above TransformMatrix
    data = np.transpose(data, axes = (2,1,0,3))
    data [:,:,:,:] = data [:,:,:,::-1]
    data = np.ndarray.flatten(data)
    data = data.newbyteorder('S').astype('>f')
    data = bytearray (data)
    data = np.asarray(data).astype(np.uint8)
    data = data.tostring()
    compressed = False
    data = zlib.compress(data);compressed = True # comment this line 4 uncompressed MHA file
    data_size=len (data)
    OK=True
    try:
        filename = basename+'_'+arrayname+'.mha'
        with open(os.path.join(dirname,filename), "wb") as f:
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
            f.write('ElementNumberOfChannels = '+str(int(ncomponents))+'\n')
            f.write('ElementType = MET_FLOAT\n')     
            f.write('ElementDataFile = LOCAL\n')  
            f.write (data)    
    except: showerror("Write file", "Unable to write output file ",filename);OK=False
      
if OK: showinfo("Done", "File convert successful")
   







