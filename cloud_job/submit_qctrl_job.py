#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"


'''
Submits job to IBM HW using Q-CTRL Fire Opal
Records meta-data containing job_id 
HD5 arrays contain input images and QCrank circuits

Fire Opal provides error suppression via optimized compilation and error mitigation
Dependence: fire-opal, qiskit

Use case:
 ./submit_qctrl_job.py -n 100  -E -i 2  --backend ibm_kingston

Fire Opal portal:
https://q-ctrl.com/products/fire-opal

'''
import sys,os
import numpy as np
from pprint import pprint
#from time import time, localtime
#from datetime import datetime
#import pytz
#import hashlib
        
import fireopal as fo
from qiskit import qasm2

from toolbox.Util_IOfunc import dateT2Str
from toolbox.Util_H5io4 import  write4_data_hdf5
from toolbox.Util_QiskitV2 import  circ_depth_aziz, harvest_circ_transpMeta

from submit_ibmq_job import commandline_parser
from submit_ibmq_job import buildPayloadMeta, construct_random_inputs, harvest_submitMeta

sys.path.append(os.path.abspath("/qcrank_light"))
from datacircuits.ParametricQCrankV2 import  ParametricQCrankV2 as QCrankV2


#=================================
#================================= 
#  M A I N 
#=================================
#=================================
if __name__ == "__main__":
    np.set_printoptions(precision=3)
    args=commandline_parser(backName='ibm_kingston',provName="QCTRL_fireopal")
    outPath=os.path.join(args.basePath,'jobs')
    assert os.path.exists(outPath)
    
    # Fire Opal works with IBM backends
    assert 'ibm' in args.backend, "Fire Opal requires IBM backend names (e.g., ibm_kingston)"
    
    expMD=buildPayloadMeta(args)
    pprint(expMD)
    expD=construct_random_inputs(expMD)
         
    # generate parametric circuit
    nq_addr, nq_data = args.numQubits
    qcrankObj = QCrankV2( nq_addr, nq_data, useCZ=args.useCZ, measure=True, barrier=not args.noBarrier , mockCirc=args.mockCirc )

    qcP=qcrankObj.circuit
    cxDepth=qcP.depth(filter_function=lambda x: x.operation.name == 'cx')
    harvest_circ_transpMeta(qcP,expMD,'ideal')
    nqTot=qcP.num_qubits
    print('M: ideal gates count:', qcP.count_ops())
    if args.verb>2 or nq_addr<4:  print(qcrankObj.circuit.draw())
    
 
    # Fire Opal uses ideal circuits (no pre-transpilation needed)
    # It handles transpilation and error suppression internally
    circ_depth_aziz(qcP,'ideal')
    
    # -------- bind the data to parametrized circuit  -------
    qcrankObj.bind_data(expD['inp_udata'])
    
    # generate the instantiated circuits
    qcEL = qcrankObj.instantiate_circuits()
    nCirc=len(qcEL)
    
    if args.verb>2 :
        print(f'.... FIRST INSTANTIATED CIRCUIT .............. of {nCirc}')
        print(qcEL[0].draw('text', idle_wires=False))
        
    print('M:  %d circuits with %d qubits are ready for Fire Opal'%(nCirc,nqTot))
    if args.verb>1: print('circ ops count:',qcEL[0].count_ops())
      
    if not args.executeCircuit:
        pprint(expMD)
        print('\nNO execution of circuit, use -E to execute the job\n')
        exit(0)
    
    # ----- Fire Opal authentication and submission ----------
    print('M: authenticating with Q-CTRL Fire Opal ...')
    
    # Get credentials from environment variables
    qctrl_api_key = os.getenv("QCTRL_API_KEY")
    assert qctrl_api_key is not None, "QCTRL_API_KEY environment variable must be set"
    

    token = os.getenv("QISKIT_IBM_TOKEN")
    instance = os.getenv("QISKIT_IBM_INSTANCE")
    assert token is not None, "QISKIT_IBM_TOKEN environment variable must be set"
    assert instance is not None, "QISKIT_IBM_INSTANCE environment variable must be set"
    
    # Authenticate with Q-CTRL
    fo.authenticate_qctrl_account(api_key=qctrl_api_key)
    print('M: Q-CTRL authentication successful')
    
    # Create IBM credentials for Fire Opal
    ibm_credentials = fo.credentials.make_credentials_for_ibm_cloud(
        token=token,  instance=instance   )
    
    # Convert circuits to QASM format (required by Fire Opal)
    print('M: converting circuits to QASM format...')
    qasmL = [qasm2.dumps(qc) for qc in qcEL]
    
    # Submit to Fire Opal
    numShots = expMD['submit']['num_shots']
    backend_name = args.backend
    
    print('M: submitting job to Fire Opal, nCirc=%d  nq=%d  shots/circ=%d at %s  ...'%(nCirc,nqTot,numShots,backend_name))
    
    fire_opal_job = fo.execute(
        circuits=qasmL,
        shot_count=numShots,
        credentials=ibm_credentials,
        backend_name=backend_name
    )
    
    # Debug: inspect Fire Opal job object attributes
    if args.verb > 1:
        print('M: FireOpal job attributes:', [x for x in dir(fire_opal_job) if not x.startswith('__')])
    
    # Get Action ID from Fire Opal job
    # The Action ID is available via the status() method
    print('M: retrieving Fire Opal Action ID...')
    status_dict = fire_opal_job.status()
    #print('sss',status_dict )  # {'status_message': 'Job has been submitted to Q-CTRL.', 'action_status': 'PENDING'}
    job_id = str(fire_opal_job.action_id)
    
    print('M: Fire Opal Action ID:', job_id)
   
    harvest_submitMeta(job_id, expMD, args)
    
    # Patch Fire Opal-specific metadata
    sd = expMD['submit']
    sd['fire_opal'] = True  # Mark as Fire Opal job
    sd['qctrl_function'] = 'execute'
       
    if args.verb>1: pprint(expMD)
    
    #...... WRITE  OUTPUT .........
    outF = os.path.join(outPath, expMD['short_name']+'.qctrl.h5')
    write4_data_hdf5(expD, outF, expMD)
    print('M:end --expName   %s   %s  %s '%(expMD['short_name'], expMD['hash'], args.backend))
    print('   ./retrieve_qctrl_job.py  --basePath  $basePath  --expName   %s   \n'%(expMD['short_name'] ))

    

