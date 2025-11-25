#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

'''
 Retrieve  results of IonQ job

Required INPUT:
    --expName: sim_a09172

Output:  raw  yields + meta data
'''

import time,os,sys
from pprint import pprint
import numpy as np
from toolbox.Util_H5io4 import  read4_data_hdf5, write4_data_hdf5
from qiskit_ionq import IonQProvider
#from submit_ibmq_job import harvest_sampler_results

from qiskit.providers.jobstatus import JobStatus
from toolbox.Util_IOfunc import dateT2Str, iso_to_localtime
from datetime import datetime
from time import time, sleep,localtime

from toolbox.Util_QiskitV2 import pack_counts_to_numpy

sys.path.append(os.path.abspath("/qcrank_light"))

from datacircuits.ParametricQCrankV2 import  qcrank_reco_from_yields


import argparse
def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--verb",type=int, help="increase output verbosity", default=1)
    parser.add_argument("--basePath",default='out',help="head dir for set of experiments")
    parser.add_argument('-e',"--expName",  default='exp_62a15b79',help='IBMQ experiment name assigned during submission')

    args = parser.parse_args()

    args.inpPath=os.path.join(args.basePath,'jobs')
    args.outPath=os.path.join(args.basePath,'meas')
    
    for arg in vars(args):  print( 'myArg:',arg, getattr(args, arg))
   
    return args

#...!...!....................
def harvest_ionq_results(job,md,bigD,T0=None):  # many circuits
    print(type(job))
    #assert isinstance(job, IonQJob)
   
    pmd=md['payload']
    #pprint(pmd)
    jobRes=job.result()  # they come from backend.run, not from Sampler()

    nCirc=pmd['num_sample']
    cntDL=jobRes.get_counts()
    if nCirc>1:
        countsL=[ cntDL[i] for i in range(nCirc) ]
    else:
        countsL=[ cntDL ] 
    #print(dir(jobRes))
    
    #print('ccc',cntDL)
    #1nCirc=len(cntDL)  # gives wrong value for 1 circuits

    qa={}
    jstat=str(job.status())
    qa['timestamp_running']='no qsec data'
    res0=jobRes.results[0]
    # collect job performance info

    qa['status']=jstat
    qa['num_circ']=nCirc
    qa['shots']=res0.shots
        
    print('job QA'); pprint(qa)
    md['job_qa']=qa
    bigD['rec_udata'], bigD['rec_udata_err'] =  qcrank_reco_from_yields(countsL,pmd['nq_addr'],pmd['nq_data'])

        
#=================================
#=================================
#  M A I N
#=================================
#=================================
if __name__ == "__main__":
    args=get_parser()
    
    inpF=args.expName+'.iqm.h5'
    expD,expMD=read4_data_hdf5(os.path.join(args.inpPath,inpF),verb=args.verb)
      
    pprint(expMD['submit'])

    if args.verb>1: pprint(expMD)

    if 0:    #example decode one Qasm circuit
        rec2=expD['circQasm'][1].decode("utf-8") 
        print('qasm circ:',type(rec2),rec2)
    
    jid=expMD['submit']['job_id']
    backType=expMD['submit']['backend_type']
    
    # ------  construct sampler-job w/o backend ------
    
    print('M: retrieve jid:',jid,backType)
    provider = IonQProvider()
    if 'qpu' in backType:
        backend = provider.get_backend(backType)
    else:
        backend= provider.get_backend("simulator")
        
    job=backend.retrieve_job(jid)
    T0=time()
    i=0
    while True:
        jstat=job.status()
        elaT=time()-T0
        print('M:i=%d  status=%s, elaT=%.1f sec'%(i,jstat,elaT))
        if jstat==JobStatus.DONE: break
        if jstat==JobStatus.ERROR: exit(99)
        i+=1; sleep(20)
    print('M: got results')#, type(job))

    harvest_ionq_results(job,expMD,expD)

   
    if args.verb>2: pprint(expMD)
    
    #...... WRITE  OUTPUT .........
    outF=os.path.join(args.outPath,expMD['short_name']+'.meas.h5')
    write4_data_hdf5(expD,outF,expMD)

    txt=''
    if expMD['payload']['num_sample']==1 and  expMD['payload']['cal_1M1']: txt='  --onlyCalibSamp '
    
    print('   ./postproc_qcrank.py  --basePath  $basePath  --expName   %s   -p a %s  -Y\n'%(expMD['short_name'],txt))
