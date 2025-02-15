#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"


'''
runs localy  or on cloud (needd creds)

Records meta-data containing  job_id 
HD5 arrays contain input and output
Use sampler and manual transpiler
Dependence:  qiskit 1.2


Use case:
./submit_ibmq_job.py -E  --numQubits 3 3 --numSample 15 --numShot 8000  --backend   ibm_brussels  


'''
import sys,os,hashlib
import numpy as np
from pprint import pprint
from time import time, localtime

from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler 
from qiskit_ibm_runtime.options.sampler_options import SamplerOptions

from toolbox.Util_IOfunc import dateT2Str
from toolbox.Util_H5io4 import  write4_data_hdf5, read4_data_hdf5
from toolbox.Util_QiskitV2 import  circ_depth_aziz, harvest_circ_transpMeta

sys.path.append(os.path.abspath("/qcrank_light"))
from datacircuits.ParametricQCrankV2 import  ParametricQCrankV2 as QCrankV2, qcrank_reco_from_yields


import argparse
#...!...!..................
def commandline_parser(backName="aer_ideal",provName="local sim"):
    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--verb",type=int, help="increase debug verbosity", default=1)
    parser.add_argument("--basePath",default='out',help="head dir for set of experiments")
    parser.add_argument("--expName",  default=None,help='(optional) replaces IBMQ jobID assigned during submission by users choice')
 
    # .... QCrank speciffic
    parser.add_argument('-q','--numQubits', default=[2,2], type=int,  nargs='+', help='pair: nq_addr nq_data, space separated ')
    parser.add_argument('-i','--numSample', default=10, type=int, help='num of images packed in to the job')
    parser.add_argument("--useCZ", action='store_true', default=False, help="change from CX to CZ entangelemnt")

    # .... job running
    parser.add_argument('-n','--numShot',type=int,default=2000, help="shots per circuit")
    parser.add_argument('-b','--backend',default=backName, help="tasks")
    parser.add_argument( "--rndComp", action='store_true', default=False, help="request randomized compilation , HW only ")
    parser.add_argument( "-B","--noBarrier", action='store_true', default=False, help="remove all bariers from the circuit ")
    parser.add_argument( "-E","--executeCircuit", action='store_true', default=False, help="may take long time, test before use ")
    parser.add_argument( "-e","--exportQPY", action='store_true', default=False, help="exprort parametrized circuit as QPY and metaData")
 
    '''there are 3 types of backend
    - run by local Aer:  ideal  or  fake_kyoto
    - submitted to IBM: ibm_kyoto
    '''

    args = parser.parse_args()
    
    args.provider=provName
    if 'ibm' in args.backend:
        args.provider='IBMQ_cloud'
 
    for arg in vars(args):
        print( 'myArgs:',arg, getattr(args, arg))

    assert len(args.numQubits)==2
    return args

#...!...!....................
def buildPayloadMeta(args):
    pd={}  # payload
    pd['nq_addr'],pd['nq_data']=args.numQubits
    pd['num_addr']=1<<pd['nq_addr']
    pd['num_sample']=args.numSample
    pd['num_qubit']=pd['nq_addr']+pd['nq_data']
    pd['seq_len']=pd['nq_data']*pd['num_addr']
    
    sbm={}
    sbm['num_shots']=args.numShot
    pom={}
    trm={}

    if 'ibm' in args.backend: 
        sbm['random_compilation']= args.rndComp
    else:
        sbm['random_compilation']=False
    
    md={ 'payload':pd, 'submit':sbm ,'transpile':trm, 'postproc':pom}
    if args.verb>1:  print('\nBMD:');pprint(md)
    return md


#...!...!....................
def harvest_sampler_submitMeta(job,md,args):
    sd=md['submit']
    sd['job_id']=job.job_id()
    backN=args.backend
    sd['backend']=backN     #  job.backend().name  V2
    
    t1=localtime()
    sd['date']=dateT2Str(t1)
    sd['unix_time']=int(time())
    sd['provider']=args.provider
    print('bbb',args.backend,args.expName)
    if args.expName==None:
        # the  6 chars in job id , as handy job identiffier
        md['hash']=sd['job_id'].replace('-','')[3:9] # those are still visible on the IBMQ-web
        tag=args.backend.split('_')[0]
        md['short_name']='%s_%s'%(tag,md['hash'])
    else:
        myHN=hashlib.md5(os.urandom(32)).hexdigest()[:6]
        md['hash']=myHN
        md['short_name']=args.expName

#...!...!....................
def construct_random_inputs(md,verb=1):
    pmd=md['payload']
    num_addr=pmd['num_addr']
    nq_data=pmd['nq_data']
    n_img=pmd['num_sample']

    # generate float random data
    data_inp = np.random.uniform(-1, 1., size=(num_addr, nq_data, n_img))
    if verb>2:
        print('input data=',data_inp.shape,repr(data_inp))
    bigD={'inp_udata': data_inp}
 
    return bigD

#...!...!....................
def harvest_sampler_results(job,md,bigD,T0=None):  # many circuits
    pmd=md['payload']
    qa={}
    jobRes=job.result()
    #counts=jobRes[0].data.c.get_counts()
    
    if T0!=None:  # when run locally
        elaT=time()-T0
        print(' job done, elaT=%.1f min'%(elaT/60.))
        qa['running_duration']=elaT
    else:
        jobMetr=job.metrics()
        #print('HSR:jobMetr:',jobMetr)
        qa['timestamp_running']=jobMetr['timestamps']['running']
        qa['quantum_seconds']=jobMetr['usage']['quantum_seconds']
        qa['all_circ_executions']=jobMetr['executions']
        
        if jobMetr['num_circuits']>0:
            qa['one_circ_depth']=jobMetr['circuit_depths'][0]
        else:
            qa['one_circ_depth']=None
    
    #1pprint(jobRes[0])
    nCirc=len(jobRes)  # number of circuit in the job
    jstat=str(job.status())
    
    countsL=[ jobRes[i].data.c.get_counts() for i in range(nCirc) ]

    # collect job performance info
    res0cl=jobRes[0].data.c
    qa['status']=jstat
    qa['num_circ']=nCirc
    qa['shots']=res0cl.num_shots
    
    qa['num_clbits']=res0cl.num_bits
    
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
    from qiskit_aer import AerSimulator
    from qiskit import transpile

    args=commandline_parser()
    np.set_printoptions(precision=3)
    expMD=buildPayloadMeta(args)
   
    pprint(expMD)
    expD=construct_random_inputs(expMD)
         
    # generate parametric circuit
    nq_addr, nq_data = args.numQubits
    qcrankObj = QCrankV2( nq_addr, nq_data, useCZ=args.useCZ,measure=True,barrier=not args.noBarrier )
        
    qcP=qcrankObj.circuit
    cxDepth=qcP.depth(filter_function=lambda x: x.operation.name == 'cz')
    print('.... PARAMETRIZED IDEAL CIRCUIT .............., cx-depth=%d'%cxDepth)
    nqTot=qcP.num_qubits
    print('M: ideal gates count:', qcP.count_ops())
    if args.verb>2 or nq_addr<4:  print(qcrankObj.circuit.draw())
      
    if args.exportQPY:
        from qiskit import qpy
        circF='./qcrank_nqa%d_nqd%d.qpy'%(nq_addr,nq_data)
        with open(circF, 'wb') as fd:
            qpy.dump(qc, fd)
        print('\nSaved circ1:',circF)
        exit(0)

    
    # ------  construct sampler(.) job ------
    runLocal=True  # ideal or fake backend
    outPath=os.path.join(args.basePath,'meas') 
    if 'ideal' in args.backend: 
        qcT=qcP
        transBackN='ideal'
        backend = AerSimulator()
    else:
        print('M: activate QiskitRuntimeService() ...')
        service = QiskitRuntimeService()
        if  'fake' in args.backend:
            transBackN=args.backend.replace('fake_','ibm_')
            hw_backend = service.backend(transBackN)
            backend = AerSimulator.from_backend(hw_backend) # overwrite ideal-backend
            print('fake noisy backend =', backend.name)
        else:
            outPath=os.path.join(args.basePath,'jobs')
            assert 'ibm' in args.backend
            backend = service.backend(args.backend)  # overwrite ideal-backend
            print('use true HW backend =', backend.name)          
            runLocal=False
            outPath=os.path.join(args.basePath,'jobs')
        qcT =  transpile(qcP, backend,optimization_level=3)
        qcrankObj.circuit=qcT  # pass transpiled parametric circuit back
        cxDepth=qcT.depth(filter_function=lambda x: x.operation.name == 'cz')
        print('.... PARAMETRIZED Transpiled (%s) CIRCUIT .............., cx-depth=%d'%(backend.name,cxDepth))
        print('M: transpiled gates count:', qcT.count_ops())
        if args.verb>2 or nq_addr<4:  print(qcT.draw('text', idle_wires=False))
                
        
    circ_depth_aziz(qcP,'ideal')
    circ_depth_aziz(qcT,'transpiled')
    harvest_circ_transpMeta(qcT,expMD,backend.name)
    assert os.path.exists(outPath)
   
    print('M: run on backend:',backend.name)

    # -------- bind the data to parametrized circuit  -------
    qcrankObj.bind_data(expD['inp_udata'])
    
    # generate the instantiated circuits
    qcEL = qcrankObj.instantiate_circuits()
    nCirc=len(qcEL)
    if args.verb>2 :
        print(f'.... FIRST INSTANTIATED CIRCUIT .............. of {nCirc}')
        print(qcEL[0].draw())
        
    print('M: execution-ready %d circuits with %d qubits backend=%s'%(nCirc,nqTot,backend.name))
                            
    if not args.executeCircuit:
        pprint(expMD)
        print('\nNO execution of circuit, use -E to execute the job\n')
        exit(0)
        
    # ----- submission ----------
    numShots=expMD['submit']['num_shots']
    print('M:job starting, nCirc=%d  nq=%d  shots/circ=%d at %s  ...'%(nCirc,qcEL[0].num_qubits,numShots,args.backend),backend)
   
    options = SamplerOptions()
    options.default_shots=numShots
    
    if expMD['submit']['random_compilation']: # erro mit  - works only for real HW
        options.twirling.enable_gates = True
        options.twirling.enable_measure = True
        options.twirling.num_randomizations=60
        print('M: enabled RandComp')


    sampler = Sampler(mode=backend, options=options)
    T0=time()
    job = sampler.run(tuple(qcEL))
   
    harvest_sampler_submitMeta(job,expMD,args)    
    if args.verb>1: pprint(expMD)
    
    if runLocal:
        harvest_sampler_results(job,expMD,expD,T0=T0)
        print('M: got results')
        #...... WRITE  MEAS OUTPUT .........
        outF=os.path.join(outPath,expMD['short_name']+'.meas.h5')
        write4_data_hdf5(expD,outF,expMD)        
        print('   ./postproc_qcrank.py  --expName   %s   -p a    -Y\n'%(expMD['short_name']))
    else:
        #...... WRITE  SUBMIT OUTPUT .........
        outF=os.path.join(outPath,expMD['short_name']+'.ibm.h5')
        write4_data_hdf5(expD,outF,expMD)
        print('M:end --expName   %s   %s  %s  jid=%s'%(expMD['short_name'],expMD['hash'],backend.name ,expMD['submit']['job_id']))
        print('   ./retrieve_ibmq_job.py --expName   %s   \n'%(expMD['short_name'] ))



    
