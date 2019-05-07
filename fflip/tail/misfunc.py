#!/usr/bin/env python

from __future__ import division, print_function


import os
import time
import tempfile
import shutil
                               
def replace(source_file_path, linen, substring):  # replace the target line with the given substring
    fh, target_file_path = tempfile.mkstemp()
    with open(target_file_path, "w") as target_file:
         with open(source_file_path, "r") as source_file:
            for i, line in enumerate(source_file):
                if i == linen - 1:
                    target_file.write(line.replace(line, substring))
                else:
                    target_file.write(line.replace(line, line))
    os.rename(source_file_path, source_file_path + "-last")
    shutil.move(target_file_path, source_file_path) # move the temprary to the source file path

def fit_dihedral(dp, substringch2, substringch3):
    # if we stream the torsion parameters independently, we might want to delete info in the above stream file.
    replace(dp + "toppar/c36ua_c5_dihe.str", 999, substringch2)
    replace(dp + "toppar/c36ua_c5_dihe.str", 1000, substringch3)
    replace(dp + "toppar/c36ua_c6_dihe.str", 999, substringch2)
    replace(dp + "toppar/c36ua_c6_dihe.str", 1000, substringch3)
    
    """
    open the C5 AND C6 dihedral fitting folders and fix the dihedral force constants
    """
    ## write this into a funtion and import it as we might not need it for other parameterizing process ...
    os.chdir(dp + "c5_fitting")
    os.system("rm -f done.fit *.out *.mme *.ene *.dat")
    os.system("sbatch fit.csh")
    while not os.path.isfile("done.fit"):  # check W's minimize .sh to see where this file is generated
        time.sleep(6)
    os.chdir(dp + "c6_fitting")
    os.system("rm -f done.fit *.out *.mme *.ene *.dat")
    os.system("sbatch fit.csh")
    while not os.path.isfile("done.fit"):  # check W's minimize .sh to see where this file is generated
        time.sleep(6)

def fit_dihedral_2d(dp, substringch1, counter):
    # if we stream the torsion parameters independently, we might want to delete info in the above stream file.
    os.chdir(dp + "hexene_2d_fitting")
    os.system("cp dihe_11222.str ./olds/12_iter{}.str".format(counter))
    os.chdir(dp + "toppar")
    os.system("cp c36ua_hexe_2d.str ./olds/36_iter{}.str".format(counter))
    # change the LJ before fitting dihedrals
    replace(dp + "toppar/c36ua_hexe_2d.str", 1018, substringch1)   
    """
    open the 2d fitting folders
    """
    ## write this into a funtion and import it as we might not need it for other parameterizing process ...
    os.chdir(dp + "hexene_2d_fitting")
    os.system("rm -f done.fit *.out *.mme *.ene *.dat")
    os.system("sbatch fit.csh")
    while not os.path.isfile("done.fit"):  # check W's minimize .sh to see where this file is generated
        time.sleep(30)