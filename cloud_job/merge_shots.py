#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

'''
Merge measurement results from multiple jobs into a single HDF5 file

Combines shot counts from multiple job executions to improve statistical
accuracy. Useful when running the same circuit multiple times to accumulate
more shots or when job limits restrict single-run shot counts.

Validates that all jobs have consistent payload metadata (circuit config,
backend, etc.) before merging. Updates total shot count and preserves
metadata from all merged jobs.

Usage:
  ./merge_shots.py --dataPath out/meas --expName job_abc_* --numJobs 3
  ./merge_shots.py --dataPath out/meas --expName qcr3a+12d_h1-1e_* --numJobs 5

Input:  Multiple *.meas.h5 files with pattern matching
Output: Single merged *.meas.h5 with combined shot counts and appended job info
'''

import os,sys
from toolbox.Util_H5io4 import  write4_data_hdf5, read4_data_hdf5
import copy
from pprint import pprint
import numpy as np
from toolbox.Util_QiskitV2 import pack_counts_to_numpy, unpack_numpy_to_counts
sys.path.append(os.path.abspath("/qcrank_light"))

from datacircuits.ParametricQCrankV2 import   qcrank_reco_from_yields


import argparse
def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--verbosity",type=int,choices=[0, 1, 2],  help="increase output verbosity", default=1, dest='verb')

    parser.add_argument("--dataPath",default='out/meas',help=' input & output dir')
                        
    parser.add_argument('-e',"--expName",  default=['exp_62a2_*'],help='list of retrieved experiments, blank separated')

    parser.add_argument('-k','--numJobs', default=2, type=int, help='num jobs, index will replace *')
    
    args = parser.parse_args()
    # make arguments  more flexible
 
    print( 'myArg-program:',parser.prog)
    for arg in vars(args):  print( 'myArg:',arg, getattr(args, arg))
    assert os.path.exists(args.dataPath)
    assert '*' in args.expName
    return args

#...!...!.................... merge two dictionaries that have bitstrings as keys and counts
def merge_bitstring_dicts(a, b):
    return {k: a.get(k, 0) + b.get(k, 0) for k in set(a) | set(b)}

#...!...!.................... 
def add_experiment(inpF,outD,outMD):
    #print('A: %d %s'%(ie,inpF))
    expD,expMD=read4_data_hdf5(os.path.join(args.dataPath,inpF),verb=0)
    smd=expMD['submit']
    
    cntLD=unpack_numpy_to_counts(expMD,expD)
    countLD=outD['countLD']
    nCirc=len(countLD)
    for ic in range(nCirc):
        countLD[ic]=merge_bitstring_dicts(countLD[ic], cntLD[ic])
 
    #.... add merging input info
    mrm=outMD['merge_shots']
    shots=smd['num_shots']
    name=expMD['short_name']
    assert name not in mrm['short_name'] # avoud duplicates 
    mrm['num_shots'].append(shots)
    mrm['short_name'].append(name)
    outMD['submit']['num_shots']+=shots

    #... spotcheck MD consistency
    txt1=str(expMD['payload'])
    txt2=str(outMD['payload'])
    #print('txt1',txt1)
    assert txt1==txt2
    assert outMD['submit']['backend']==expMD['submit']['backend']
             
         
#...!...!.................... 
def setup_containers(expD,expMD,numJobs):
    # for now all experiments must have the same dims
    nimg=expMD['payload']['num_sample']

    #1 ... big data...  only copy 1 input
    bigD={}
    xx='inp_udata'
    bigD[xx]=expD[xx]

    countLD=unpack_numpy_to_counts(expMD,expD)
    #print(countL)
    bigD['countLD']=countLD
    
    #2 ... meta data...                     
    MD=copy.deepcopy(expMD)
    
    # ... new merged job hash & name
    MD['hash']='%sx%d'%(expMD['hash'],numJobs)
    MD['short_name']='%sx%d'%(expMD['short_name'],numJobs)
    
    #.. payload info adjustement
    smd=MD['submit']
    smd['1st_job_ref_json']=smd.pop('job_ref_json')
    MD['merge_shots']={'num_shots':[smd['num_shots']], 'short_name':[expMD['short_name']]}

    return bigD, MD
    
#=================================
#=================================
#  M A I N 
#=================================
#=================================
if __name__=="__main__":
    args=get_parser()

    
    inpFT=args.expName+'.meas.h5'
    
    expD,expMD=read4_data_hdf5(os.path.join(args.dataPath,inpFT.replace('*','1')))
    if args.verb>1: pprint(expMD)
    outD,outMD=setup_containers(expD,expMD,args.numJobs)

    # append other experiments
    for ie in range(2,args.numJobs+1):
        add_experiment(inpFT.replace('*','%d'%ie),outD,outMD)

    print('M:merge_shots info');pprint(outMD['merge_shots'])
    if args.verb>1: pprint(outMD)

    pmd=outMD['payload']
    countsL=outD.pop('countLD')
    outD['rec_udata'], outD['rec_udata_err'] =  qcrank_reco_from_yields(countsL,pmd['nq_addr'],pmd['nq_data'])
    if 1:  # saving raw shots as well, needed when merging mutiple jobs        
        pack_counts_to_numpy(outMD,outD,countsL)

    
    #...... WRITE  OUTPUT .........
    outF=os.path.join(args.dataPath,outMD['short_name']+'.meas.h5')
    write4_data_hdf5(outD,outF,outMD)
    
    print('   ./postproc_qcrank.py --expName   %s -p a  \n'%(outMD['short_name'] ))
    #pprint(outMD)
