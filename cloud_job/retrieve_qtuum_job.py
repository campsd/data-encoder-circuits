#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

'''
 Retrieve  results of IBMQ job

Required INPUT:
    --expName: exp_j33ab44

Output:  raw  yields + meta data
'''

import time,os,sys
from pprint import pprint
import numpy as np
from toolbox.Util_H5io4 import  read4_data_hdf5, write4_data_hdf5
from toolbox.Util_QiskitV2 import pack_counts_to_numpy

import json
import qnexus as qnx
from qnexus.models.references import ExecuteJobRef
from time import time, sleep
from retrieve_ibmq_job import get_parser

sys.path.append(os.path.abspath("/qcrank_light"))
from datacircuits.ParametricQCrankV2 import   qcrank_reco_from_yields


#...!...!....................
def execTimeConverter(data):
       from datetime import datetime
       import pytz
       # Extract the Annotations.created field
       timestamp1 = data.get("annotations", {}).get("created", "Not found")
        
       # Print the extracted date
       #print("Annotations.created:", timestamp1)
       # Parse the timestamp as a datetime object with UTC timezone
       dt_utc = datetime.fromisoformat(timestamp1)
       
       # Define the California timezone (PDT/PST)
       california_tz = pytz.timezone("America/Los_Angeles")
        
       # Convert the UTC time to California time
       dt_cal = dt_utc.astimezone(california_tz)
       # Convert the datetime object to the desired format
       my_timestamp = dt_cal.strftime("%Y%m%d_%H%M%S_%Z")
       #print('ttt',my_timestamp)
       return my_timestamp

#...!...!....................
def retrieve_qtuum_job(md,bigD):
    #pprint(md)
    sbm=md['submit']
    pmd=md['payload']
    #print(sorted(md))
    
    data = json.loads(sbm['job_ref_json'])
    ref_exec= ExecuteJobRef(**data)

    jobStatus=qnx.jobs.status(ref_exec)
    #print('\nstatus3:',type(jobStatus))
    
    #print(dir(jobStatus))
    #  'cancelled_time', 'completed_time', 'count', 'df', 'error_detail', 'error_time', 'from_dict', 'index', 'message', 'queue_position', 'queued_time', 'running_time', 'status', 'submitted_time']
    stat=jobStatus.status
    print('stat:',stat) #,jobStatus.running_time)

    qnx.jobs.wait_for(ref_exec)
    results = qnx.jobs.results(ref_exec)

    nCirc=len(results)
    print('job  finished, nCirc=%d'%(nCirc))
        
    qa={}
    qa['status']=str(stat)
    qa['num_circ']=nCirc
    qa['timestamp_running']=execTimeConverter(data)

    countsL=[None]*nCirc
    for ic in range(nCirc):
        result = results[ic].download_result()
        counter=result.get_counts()
        # Convert tuple keys to bitstrings
        bitstring_dict = {"".join(map(str, reversed(key))): value for key, value in counter.items()}
        countsL[ic]=bitstring_dict 
        #print('\nis=%d  res:'%(ic)); pprint(bitstring_dict)
        
    print('job QA'); pprint(qa)
    md['job_qa']=qa
    bigD['rec_udata'], bigD['rec_udata_err'] =  qcrank_reco_from_yields(countsL,pmd['nq_addr'],pmd['nq_data'])
    
    if 1:  # saving raw shots as well, needed when merging mutiple jobs        
        pack_counts_to_numpy(md,bigD,countsL)

    return bigD    

        
#=================================
#=================================
#  M A I N
#=================================
#=================================
if __name__ == "__main__":
    args=get_parser()
            
    inpF=args.expName+'.qtuum.h5'
    expD,expMD=read4_data_hdf5(os.path.join(args.inpPath,inpF),verb=args.verb)
    
    if 0: # hack old input from ...
        pmd=expMD['payload']
        expMD['submit']['num_shots']=pmd.pop('num_shots')
        
    #pprint(expMD['submit'])

    if args.verb>1: pprint(expMD)

    
    retrieve_qtuum_job(expMD,expD)

    if args.verb>2: pprint(expMD)
    
    #...... WRITE  OUTPUT .........
    outF=os.path.join(args.outPath,expMD['short_name']+'.meas.h5')
    write4_data_hdf5(expD,outF,expMD)

    print('   ./postproc_qcrank.py  --expName   %s   -p a    -Y\n'%(expMD['short_name']))


    
    
