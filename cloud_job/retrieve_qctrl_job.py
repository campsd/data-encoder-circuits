#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

'''
 Retrieve results of Q-CTRL Fire Opal job

Required INPUT:
    --expName: exp_j33ab44

Output: raw yields + meta data
'''

import time,os,sys
from pprint import pprint
import numpy as np
from datetime import datetime
import pytz
from toolbox.Util_H5io4 import  read4_data_hdf5, write4_data_hdf5
from time import time

import fireopal as fo

sys.path.append(os.path.abspath("/qcrank_light"))
from datacircuits.ParametricQCrankV2 import  qcrank_reco_from_yields


import argparse
def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--verb",type=int, help="increase output verbosity", default=1)
    parser.add_argument("--basePath",default='out',help="head dir for set of experiments")
    parser.add_argument('-e',"--expName",  default='exp_62a15b79',help='Fire Opal experiment name assigned during submission')

    args = parser.parse_args()

    args.inpPath=os.path.join(args.basePath,'jobs')
    args.outPath=os.path.join(args.basePath,'meas')
    
    for arg in vars(args):  print( 'myArg:',arg, getattr(args, arg))
   
    return args

#...!...!....................
def harvest_fireopal_results(fire_opal_results, md, bigD):
    """Harvest results from Fire Opal result dictionary
    
    fire_opal_results: list of count dictionaries from fo.get_result()
    
    """
    pmd = md['payload']
    qa = {}
    
    # fire_opal_results is a list of count dictionaries (one per circuit)
    nCirc = len(fire_opal_results)
    
    # Convert Fire Opal results to counts list
    countsL = fire_opal_results
    
    # Collect job performance info
    qa['status'] = 'SUCCESS'  # If we got here, job succeeded
    qa['num_circ'] = nCirc

    #print('ccc',    countsL[0]); # {'00000': 0.06295299410526886, '00001': 0.004045185666765728,
    qa['timestamp_running'] = 'uknown'
    
    print('job QA'); pprint(qa)
    md['job_qa'] = qa
    
    # Reconstruct data from yields
    bigD['rec_udata'], bigD['rec_udata_err'] = qcrank_reco_from_yields(countsL, pmd['nq_addr'], pmd['nq_data'])

    

        
#=================================
#=================================
#  M A I N
#=================================
#=================================
if __name__ == "__main__":
    args=get_parser()
    
    inpF=args.expName+'.qctrl.h5'
    expD,expMD=read4_data_hdf5(os.path.join(args.inpPath,inpF),verb=args.verb)
      
    pprint(expMD['submit'])

    if args.verb>1: pprint(expMD)
    
    job_id=expMD['submit']['job_id']

    # ------  authenticate with Q-CTRL ------
    print('M: authenticating with Q-CTRL Fire Opal ...')
    qctrl_api_key = os.getenv("QCTRL_API_KEY")
    assert qctrl_api_key is not None, "QCTRL_API_KEY environment variable must be set"
    
    fo.authenticate_qctrl_account(api_key=qctrl_api_key)
    #print('M: Q-CTRL authentication successful')
    
    print('M: retrieve Fire Opal job_id:',job_id)

         
    print(f'M: retrieving results using Action ID: {job_id}')
    print('   (this will poll until job completes)')
        
    T0=time()
        
    # Use fo.get_result() which polls until completion
    resultD = fo.get_result(job_id)
        
    elaT = time()-T0
    print(f'M: got results, elaT=%.1f sec' % elaT)
        
    # Fire Opal result format: {'results': [...], 'provider_job_ids': [...]}
    #print(sorted(resultD))  # ['execution_results', 'provider_job_ids', 'results']

    fire_opal_results = resultD["results"]
    harvest_fireopal_results(fire_opal_results, expMD, expD)
    expMD['job_qa']['provoder_job_id'] = resultD["provider_job_ids"][0]        

    if 0: # patch md
        #pom= expMD['postproc']
        expMD['submit']['random_compilation']=False
        
    if args.verb>2: pprint(expMD)
    
    #...... WRITE  OUTPUT .........
    outF=os.path.join(args.outPath,expMD['short_name']+'.meas.h5')
    write4_data_hdf5(expD,outF,expMD)


    print('   ./postproc_qcrank.py  --basePath  $basePath  --expName   %s   -p a    -Y\n'%(expMD['short_name']))
  
    
    

