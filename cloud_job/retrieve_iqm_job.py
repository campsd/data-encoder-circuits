#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

'''
 Retrieve  results of IQM job

Required INPUT:
    --expName: exp_j33ab44

Output:  raw  yields + meta data
'''

import time,os,sys
from pprint import pprint
import numpy as np
from toolbox.Util_H5io4 import  read4_data_hdf5, write4_data_hdf5
from iqm.qiskit_iqm import IQMProvider ,IQMJob
from qiskit.providers.jobstatus import JobStatus

from toolbox.Util_IOfunc import dateT2Str
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
def harvest_iqm_results(job,md,bigD,T0=None):  # many circuits
    assert isinstance(job, IQMJob)
   
    pmd=md['payload']
    qa={}
    jobRes=job.result()  # they come from backend.run, not from Sampler()

    cntDL=jobRes.get_counts()
    #print(dir(jobRes))

    
    def time_diff_sec(x, y):
        dt1 = datetime.fromisoformat(x)
        dt2 = datetime.fromisoformat(y)
        time_diff = dt2 - dt1
        return time_diff.total_seconds()

 

    #pprint(jobRes.to_dict())
    tstampD=jobRes.timestamps
    #pprint(tstampD)

    t0=tstampD['compile_start']
    t1=tstampD['execution_start']
    t2=tstampD['execution_end']
    qa['quantum_seconds']= time_diff_sec(t0,t2)
    qa['timestamp_running']=dateT2Str(iso_to_localtime(t2))
    
    
    '''
           if jobMetr['num_circuits']>0:
                qa['one_circ_depth']=jobMetr['circuit_depths'][0]
            else:
       
    '''

    nCirc=len(cntDL)
    jstat=str(job.status())
    
    countsL=[ cntDL[i] for i in range(nCirc) ]

    res0=jobRes.results[0]
    # collect job performance info

    qa['status']=jstat
    qa['num_circ']=nCirc
    qa['shots']=res0.shots
    qa['calib_id']=  res0._metadata['calibration_set_id']
        
    print('job QA'); pprint(qa)
    md['job_qa']=qa
    bigD['rec_udata'], bigD['rec_udata_err'] =  qcrank_reco_from_yields(countsL,pmd['nq_addr'],pmd['nq_data'])

    return bigD

        
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
    #1jid='cns2cfhqygeg00879yv0' # smapler,  cairo

    # ------  construct sampler-job w/o backend ------
    qpuName=expMD['submit']['backend']
    print('M: access IQM backend ...',qpuName)
    provider=IQMProvider(url="https://cocos.resonance.meetiqm.com/"+qpuName)
    backend = provider.get_backend()
    print('got BCKN:',backend.name,qpuName)
   
    print('M: retrieve jid:',jid)
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
    print('M: got results', type(job))
        
    harvest_iqm_results(job,expMD,expD)
   
    if args.verb>2: pprint(expMD)
    
    #...... WRITE  OUTPUT .........
    outF=os.path.join(args.outPath,expMD['short_name']+'.meas.h5')
    write4_data_hdf5(expD,outF,expMD)


    print('   ./postproc_qcrank.py  --expName   %s   -p a    -Y\n'%(expMD['short_name']))
