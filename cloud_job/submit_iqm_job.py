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

#from pytket.extensions.qiskit import qiskit_to_tk   # needed by Qtuum
from iqm.qiskit_iqm import IQMProvider, transpile_to_IQM #,IQMJob

from toolbox.Util_IOfunc import dateT2Str
from toolbox.Util_H5io4 import  write4_data_hdf5, read4_data_hdf5
from toolbox.Util_QiskitV2 import  circ_depth_aziz, harvest_circ_transpMeta

from submit_ibmq_job import commandline_parser

from submit_ibmq_job import buildPayloadMeta, construct_random_inputs, harvest_submitMeta
from datacircuits.ParametricQCrankV2 import  ParametricQCrankV2 as QCrankV2, qcrank_reco_from_yields

#...!...!....................
def XXpush_circ_to_nexus(qcL,md):
    myHN=hashlib.md5(os.urandom(32)).hexdigest()[:6]
    md['hash']=myHN
    nCirc=len(qcL)
    
    print('uploadeing %d circuits '%(nCirc))
    t0=time()
    crefL=[None]*nCirc
    for ic in range(nCirc):
        circN='c%d_%s'%(ic,myHN)
        crefL[ic]=qnx.circuits.upload(circuit=qcL[ic], name=circN)
        print('ic:',ic, circN) #,crefL[ic])
    t1=time()
    print('elaT=%.1f sec, %d circuits uploaded'%(t1-t0,nCirc))
    return crefL

#...!...!....................
def XXcompile_qtuum_circuits(crefL,md):
    nCirc=len(crefL)
    sbm=md['submit']
    sbm['user_group']='CHM170'  #tmp
    sbm['backend']=args.backend

    
    #.... add more meta-date
    if args.expName==None:
        tag='emu' if args.backend=='H1-1E' else 'hw'
        md['short_name']='%s_%s'%(tag,md['hash'])
    else:
        md['short_name']=args.expName
    #print(md)
    
    #?backN=args.backend
    #?if args.backend=='ideal':  backN='H1-1E'
    #??else: backN='H1-1'
        
    devConf1 = qnx.QuantinuumConfig(device_name=sbm['backend'],user_group=sbm['user_group'])
    #print('use devConf:',devConf1)
    
    #...  compile list of circs at once
    t0=time()
    refCL=qnx.compile( circuits=crefL, name='comp_'+md['hash'],
                       optimisation_level=2, backend_config=devConf1,
                       project=project )
    t1=time()
    print('elaT=%.1f sec, compiled.'%(t1-t0))

    #... get cost
    nCirc=len(refCL)
    shots=sbm['num_shots']
    for ic in range(nCirc):
        cost=qnx.circuits.cost( circuit_ref=refCL[ic],n_shots=shots,
                                backend_config=devConf1, syntax_checker="H1-1SC"  )
        print('is=%d shots=%d cost=%.1f'%(ic,shots,cost))
        break
    return refCL,devConf1

#...!...!....................
def XXsubmit_qtuum__circuits(ccrefL,devConf,md):
    nCirc=len(ccrefL)
    sbm=md['submit']
    t0=time()
    shotL=[sbm['num_shots']]*nCirc
    ref_exec= qnx.start_execute_job( circuits=ccrefL, n_shots=shotL,
                                     backend_config=devConf,name="exec_"+md['hash'])
    t1=time()
    print('nCirc=%d  submit elaT=%.1f  hash=%s\n'%(nCirc,t1-t0,md['hash']))

    sbm['job_ref_json']=ref_exec.model_dump_json()
    
    #.... harvest meta data
    t1=localtime()
    sbm['date']=dateT2Str(t1)
    sbm['unix_time']=int(time())
    sbm['num_circ']=nCirc
    pprint(sbm)
    
    
#=================================
#=================================
#  M A I N 
#=================================
#=================================
if __name__ == "__main__":
    np.set_printoptions(precision=3)
    args=commandline_parser(backName='deneb',provName="IQM_cloud")
    outPath=os.path.join(args.basePath,'jobs')
    assert os.path.exists(outPath)

    assert args.backend in  ['garnet', 'sirius', 'deneb']
    
    expMD=buildPayloadMeta(args)
    pprint(expMD)
    expD=construct_random_inputs(expMD)
         
    # generate parametric circuit
    nq_addr, nq_data = args.numQubits
    qcrankObj = QCrankV2( nq_addr, nq_data,measure=True,barrier=not args.noBarrier )

    qcP=qcrankObj.circuit
    cxDepth=qcP.depth(filter_function=lambda x: x.operation.name == 'cz')
    print('.... PARAMETRIZED IDEAL CIRCUIT .............., cx-depth=%d'%cxDepth)
    harvest_circ_transpMeta(qcP,expMD,'ideal')
    nqTot=qcP.num_qubits
    print('M: ideal gates count:', qcP.count_ops())
    if args.verb>2 or nq_addr<4:  print(qcrankObj.circuit.draw())


    assert 'ideal' not  in args.backend
    
    # ------  construct backend.run() because IQM does not support Qiskit Sampler()------


    qpuName=args.backend
    print('M: access IQM backend ...',qpuName)
    provider=IQMProvider(url="https://cocos.resonance.meetiqm.com/"+qpuName)
    backend = provider.get_backend()
    print('got BCKN:',backend.name,qpuName)
    
    qcT = transpile_to_IQM(qcP, backend)        
    qcrankObj.circuit=qcT  # pass transpiled parametric circuit back
    cxDepth=qcT.depth(filter_function=lambda x: x.operation.name == 'cz')
    print('.... PARAMETRIZED Transpiled (%s) CIRCUIT .............., cx-depth=%d'%(backend.name,cxDepth))
    print('M: transpiled gates count:', qcT.count_ops())
    if args.verb>2 or nq_addr<2:  print(qcT.draw('text', idle_wires=False))
                
    circ_depth_aziz(qcP,'ideal')
    circ_depth_aziz(qcT,'transpiled')
    harvest_circ_transpMeta(qcT,expMD,backend.name)

        
    # -------- bind the data to parametrized circuit  -------
    qcrankObj.bind_data(expD['inp_udata'])
    
    # generate the instantiated circuits
    qcEL = qcrankObj.instantiate_circuits()
    nCirc=len(qcEL)
    if args.verb>2 :
        print(f'.... FIRST INSTANTIATED CIRCUIT .............. of {nCirc}')
        print(qcEL[0].draw())
        
    print('M:  %d circuits with %d qubits are ready'%(nCirc,nqTot))
    if args.verb>1: print('circ commands:\n',qcEL[0].get_commands())
      
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
    print('   ./retrieve_iqm_job.py --expName   %s   \n'%(expMD['short_name'] ))

    
