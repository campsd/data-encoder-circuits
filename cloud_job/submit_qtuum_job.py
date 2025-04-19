#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"


'''
Submits job to Qtuum cloud
Records meta-data containing  job_id 
HD5 arrays contain input images and QCrank circuits

Dependence: qpixl, qiskit

Nexus web API: https://nexus.quantinuum.com/jobs 

???Possible backends
['H1-1SC', 'H1-1E', 'H2-1E', 'H1-1', 'H2-1SC', 'H2-1','ideal']

--backend : selects backend

Use case:
 ./submit_qtuum_job.py -n 100  -E -i 2

Web portal
https://um.qapi.quantinuum.com/user

'''
import sys,os,hashlib
import numpy as np
from pprint import pprint
from time import time, localtime
import qnexus as qnx

from pytket.extensions.qiskit import qiskit_to_tk   # needed by Qtuum

from toolbox.Util_IOfunc import dateT2Str
from toolbox.Util_H5io4 import  write4_data_hdf5, read4_data_hdf5
from toolbox.Util_QiskitV2 import  harvest_circ_transpMeta

from submit_ibmq_job import commandline_parser

from submit_ibmq_job import buildPayloadMeta, construct_random_inputs
from datacircuits.ParametricQCrankV2 import  ParametricQCrankV2 as QCrankV2, qcrank_reco_from_yields

#...!...!....................
def push_circ_to_nexus(qcL,md):
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
def compile_qtuum_circuits(crefL,md):
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
def submit_qtuum__circuits(ccrefL,devConf,md):
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
    args=commandline_parser(backName='H1-1E',provName="Qtuum_cloud")
    outPath=os.path.join(args.basePath,'jobs')
    assert os.path.exists(outPath)
    
    np.set_printoptions(precision=3)
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
        
    qcTketL=[  qiskit_to_tk(qc) for qc in qcEL]        
    if not args.executeCircuit:
        pprint(expMD)
        print('\nNO execution of circuit, use -E to execute the job\n')
        exit(0)
        
    # ----- submission ----------
    numShots=expMD['submit']['num_shots']
    print('M:job starting, nCirc=%d  nq=%d  shots/circ=%d at %s  ...'%(nCirc,qcTketL[0].n_qubits,numShots,args.backend))

    #qnx.login_with_credentials()
    project = qnx.projects.get_or_create(name="qcrank-feb-15")
    qnx.context.set_active_project(project)
   
    crefL=push_circ_to_nexus(qcTketL,expMD)
    ccrefL,devConf=compile_qtuum_circuits(crefL,expMD)

    #.... execution     
    submit_qtuum__circuits(ccrefL,devConf,expMD)

    #...... WRITE  OUTPUT .........
    outF=os.path.join(outPath,expMD['short_name']+'.qtuum.h5')
    write4_data_hdf5(expD,outF,expMD)
    print('M:end --expName   %s   %s  %s '%(expMD['short_name'],expMD['hash'], args.backend))
    print('   ./retrieve_qtuum_job.py --expName   %s   \n'%(expMD['short_name'] ))

    
