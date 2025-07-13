#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"


'''
Submits job to IQM cloud
Records meta-data containing  job_id 
HD5 arrays contain input images and QCrank circuits

Dependence: qpixl, qiskit

Nexus web API: https://nexus.quantinuum.com/jobs 

Possible backends: ['garnet', 'sirius', 'deneb']
For ideal circuit use : ./submit_ibmq_job.py

will transpiler parametric circuits

Use case:
 ./submit_iqm_job.py -n 100  -E -i 2

Web portal
https://resonance.meetiqm.com/jobs

'''
import sys,os,hashlib
import numpy as np
from pprint import pprint
from time import time, localtime

from iqm.qiskit_iqm import IQMProvider, transpile_to_IQM 

from toolbox.Util_IOfunc import dateT2Str
from toolbox.Util_H5io4 import  write4_data_hdf5, read4_data_hdf5
from toolbox.Util_QiskitV2 import  circ_depth_aziz, harvest_circ_transpMeta

from submit_ibmq_job import commandline_parser

from submit_ibmq_job import buildPayloadMeta, construct_random_inputs, harvest_submitMeta
from datacircuits.ParametricQCrankV2 import  ParametricQCrankV2 as QCrankV2, qcrank_reco_from_yields


#=================================
#================================= 
#  M A I N 
#=================================
#=================================
if __name__ == "__main__":
    np.set_printoptions(precision=3)
    args=commandline_parser(backName='sirius',provName="IQM_cloud")
    outPath=os.path.join(args.basePath,'jobs')
    assert os.path.exists(outPath)

    assert args.backend in  ['garnet', 'sirius','emerald']   # OLD , 'deneb'
    
    expMD=buildPayloadMeta(args)
    pprint(expMD)
    expD=construct_random_inputs(expMD)
         
    # generate parametric circuit
    nq_addr, nq_data = args.numQubits
    qcrankObj = QCrankV2( nq_addr, nq_data,measure=True,barrier=not args.noBarrier )

    qcP=qcrankObj.circuit
    cxDepth=qcP.depth(filter_function=lambda x: x.operation.name == 'cx')
    print('.... PARAMETRIZED IDEAL CIRCUIT .............., cx-depth=%d'%cxDepth)
    harvest_circ_transpMeta(qcP,expMD,'ideal')
    nqTot=qcP.num_qubits
    print('M: ideal gates count:', qcP.count_ops())
    if args.verb>2 or nq_addr<4:  print(qcrankObj.circuit.draw())
    
    if args.exportQPY:
        from qiskit import qpy
        circF='out/qcrank_nqa%d_nqd%d.qpy'%(nq_addr,nq_data)
        with open(circF, 'wb') as fd:
            qpy.dump(qcP, fd)
        print('\nSaved circ1:',circF)
        exit(0)

    assert 'ideal' not  in args.backend
    
    # ------  construct backend.run() because IQM does not support Qiskit Sampler()------

    qpuName=args.backend
    print('M: access IQM backend ...',qpuName)
    provider=IQMProvider(url="https://cocos.resonance.meetiqm.com/"+qpuName)
    backend = provider.get_backend()
    print('got BCKN:',backend.name,qpuName)
    
    qcT = transpile_to_IQM(qcP, backend, seed_transpiler=args.transpSeed)        
    qcrankObj.circuit=qcT  # pass transpiled parametric circuit back
    cxDepth=qcT.depth(filter_function=lambda x: x.operation.name in ['cz', 'move'])
    print('.... PARAMETRIZED Transpiled (%s) CIRCUIT .............., cz+move-depth=%d'%(backend.name,cxDepth))
    print('M: transpiled gates count:', qcT.count_ops())
    if args.verb>2 or nq_addr<2:  print(qcT.draw('text', idle_wires=False))
                
    circ_depth_aziz(qcP,'ideal')
    circ_depth_aziz(qcT,'transpiled')
    harvest_circ_transpMeta(qcT,expMD,qpuName)

        
    # -------- bind the data to parametrized circuit  -------
    qcrankObj.bind_data(expD['inp_udata'])
    
    # generate the instantiated circuits
    qcEL = qcrankObj.instantiate_circuits()
    nCirc=len(qcEL)
    if args.verb>2 :
        print(f'.... FIRST INSTANTIATED CIRCUIT .............. of {nCirc}')
        print(qcEL[0].draw('text', idle_wires=False))
        
    print('M:  %d circuits with %d qubits are ready'%(nCirc,nqTot))
    if args.verb>1: print('circ ops count:',qcEL[0].count_ops())
      
    if not args.executeCircuit:
        pprint(expMD)
        print('\nNO execution of circuit, use -E to execute the job\n')
        exit(0)
        
    # ----- submission ----------
    numShots=expMD['submit']['num_shots']
    print('M:job starting, nCirc=%d  nq=%d  shots/circ=%d at %s  ...'%(nCirc,qcEL[0].num_qubits,numShots,args.backend))

  
    job = backend.run(qcEL, shots=args.numShot)

    harvest_submitMeta(job,expMD,args) 
    
    #...... WRITE  OUTPUT .........
    outF=os.path.join(outPath,expMD['short_name']+'.iqm.h5')
    write4_data_hdf5(expD,outF,expMD)
    print('M:end --expName   %s   %s  %s '%(expMD['short_name'],expMD['hash'], args.backend))
    print('   ./retrieve_iqm_job.py  --basePath  $basePath  --expName   %s   \n'%(expMD['short_name'] ))

    
