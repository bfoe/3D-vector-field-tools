# 3D vector field tools
This is a collection of tools for vector field IO e.g. format confersion, simulation etc.
## Digital_Phantom:
creates a digial phantom for flow simulations that consists of a simple cylindrical tube
by simulating the Hagen-Poiseuille equation: https://en.wikipedia.org/wiki/Hagen%E2%80%93Poiseuille_equation
used to check permeability simulation with Thermo Fischer Scientific's Digital Rock analysis software
http://www.fei.com/software/pergeos-for-oil-gas
## ITK_Convert
general purpose vector field format converter
uses ITK to convert whatever format ITK can read and write
## MHAcompare
compare two 3D vector fields in MHA format
and returns two similarity measures in MHA format
## fld2mha - mha2fld
convert between AVS "*.fld" vector field files created by PerGEOS and "*.mha" format
## permeability.cpp
This file is a modified version of the original which is part of the Palabos library:
http://www.palabos.org/documentation/tutorial/permeability.html#simulation
## txt2mha
#reads "*.txt" vector field files created as regular grid by ComSol (https://www.comsol.com/)
and converts to "*.mha" format
## vti2mha
uses VTK to convert VTI format to MHA (e.g. output from permeability.cpp output) 
