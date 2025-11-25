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
from time import time, localtime,mktime
from datetime import datetime, timezone

from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler 
from qiskit_ibm_runtime.options.sampler_options import SamplerOptions
from datetime import datetime


from toolbox.Util_IOfunc import dateT2Str, iso_to_localtime, iso_to_pt_time
from toolbox.Util_H5io4 import  write4_data_hdf5, read4_data_hdf5
from toolbox.Util_QiskitV2 import  circ_depth_aziz, harvest_circ_transpMeta
from qiskit_aer import AerSimulator
from qiskit import transpile
from qiskit import qpy
        
sys.path.append(os.path.abspath("/qcrank_light"))
from datacircuits.ParametricQCrankV2 import  ParametricQCrankV2 as QCrankV2, qcrank_reco_from_yields


import argparse
#...!...!..................
def commandline_parser(backName="aer_ideal",provName="local_sim"):
    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--verb",type=int, help="increase debug verbosity", default=1)
    parser.add_argument("--basePath",default='out',help="head dir for set of experiments")
    parser.add_argument("--expName",  default=None,help='(optional) replaces IBMQ jobID assigned during submission by users choice')
 
    # .... QCrank speciffic
    parser.add_argument('-q','--numQubits', default=[2,2], type=int,  nargs='+', help='pair: nq_addr nq_data, space separated ')
    parser.add_argument('-i','--numSample', default=10, type=int, help='num of images packed in to the job')
    parser.add_argument('--rndSeed', default=None, type=int, help='(optional) freezes randominput sequence')
    parser.add_argument("--useCZ", action='store_true', default=False, help="change from CX to CZ entangelemnt")
    parser.add_argument("--mockCirc", action='store_true', default=False, help="changes Ry to make circ look nice but non-executable")
    parser.add_argument("-A","--add1M1data", action='store_true', default=False, help="append circ w/ +1,-1, pattern along num_addr")


    # .... job running
    parser.add_argument('-n','--numShot',type=int,default=2000, help="shots per circuit")
    parser.add_argument('-b','--backend',default=backName, help="tasks")
    parser.add_argument('--transpSeed',default=42, type=int, help="random seed for transpiler")
    parser.add_argument( "--useRC", action='store_true', default=False, help="enable randomized compilation , HW only ")
    parser.add_argument( "--useDD", action='store_true', default=False, help="enable Dynamical Decoupling , HW only ")


    parser.add_argument( "-B","--noBarrier", action='store_true', default=False, help="remove all bariers from the circuit ")
    parser.add_argument( "-E","--executeCircuit", action='store_true', default=False, help="may take long time, test before use ")
    parser.add_argument( "-e1","--exportQPY1", action='store_true', default=False, help="exprort parametrized circuit as QPY")
    parser.add_argument( "-e2","--exportQPY2", action='store_true', default=False, help="exprort binded circuit w/ meta as QPY and metaData")
 
    '''there are 3 types of backend
    - run by local Aer:  ideal  or  fake_kyoto
    - submitted to IBM: ibm_kyoto
    '''

    args = parser.parse_args()
    
    args.provider=provName
    if 'ibm' in args.backend  and 'local' in args.provider :
        args.provider='IBMQ_cloud'
 
    for arg in vars(args):
        print( 'myArgs:',arg, getattr(args, arg))

    assert len(args.numQubits)==2
    return args

#...!...!....................
def M_export_qpy_parm(qc):
    circF='out/qcrank_nqa%d_nqd%d_param.qpy'%(nq_addr,nq_data)
    with open(circF, 'wb') as fd:
        qpy.dump(qc, fd)
    print('\nSaved 1 circ:',circF)

#...!...!....................
def M_export_qpy_bound():
    inpData=expD['inp_udata']
    qcrankObj.bind_data(inpData)
    qcEL = qcrankObj.instantiate_circuits()
    circF='out/qcrank_nqa%d_nqd%d_bound.qpy'%(nq_addr,nq_data)
    nCirc=len(qcEL)
    for ic in range(nCirc):
        data=inpData[...,ic].flatten()
        qcEL[ic].metadata = {  "name":"image_%d"%ic, "inp_data": data.tolist(),
                               "nq_addr":nq_addr,"nq_data":nq_data}
        
    with open(circF, 'wb') as fd:
        qpy.dump(qcEL, fd)
    print('\nSaved %d circs:'%(nCirc),circF)
    nshot=(1<<nq_addr)*3000
    print('exec:  ./run_qpy_bound.py --input %s --nshot %d --backendType 2'%(circF, nshot))
    exit(99)

#...!...!....................
def buildPayloadMeta(args):
    pd={}  # payload
    pd['nq_addr'],pd['nq_data']=args.numQubits
    pd['num_addr']=1<<pd['nq_addr']
    pd['num_sample']=args.numSample+args.add1M1data
    pd['num_qubit']=pd['nq_addr']+pd['nq_data']
    pd['seq_len']=pd['nq_data']*pd['num_addr']
    pd['rnd_seed']=args.rndSeed
    pd['cal_1M1']=args.add1M1data
    sbm={}
    sbm['num_shots']=args.numShot
    pom={}
    
    tmd={}
    tmd['transp_seed']=args.transpSeed
    
    if 'ibm' in args.backend: 
        sbm['random_compilation']= args.useRC
        sbm['dynamical_decoupling']= args.useDD
    else:
        sbm['random_compilation']=False
        sbm['dynamical_decoupling']=False

    md={ 'payload':pd, 'submit':sbm ,'transpile':tmd, 'postproc':pom}
    if args.verb>1:  print('\nBMD:');pprint(md)
    return md


#...!...!....................
def harvest_submitMeta(job_id,md,args):
    sd=md['submit']
    sd['job_id']=job_id
    backN=args.backend
    sd['backend']=backN     
    
    t1=localtime()
    sd['date']=dateT2Str(t1)
    sd['unix_time']=int(time())
    sd['provider']=args.provider
        
    if args.expName==None:
        # the  6 chars in job id , as handy job identiffier
        md['hash']=sd['job_id'].replace('-','')[3:9] # those are still visible on the IBMQ-web
        if args.provider=='IBMQ_cloud' :
            tag=args.backend.split('_')[1]
        if args.provider=='QCTRL_fireopal' :
            tag=args.backend.split('_')[1]+'FO'
        if args.provider=="IQM_cloud":
            tag=args.backend.split('_')[0]
        if args.provider=="IonQ_cloud":
            tag=args.backend #.split('_')[0]
            #if 'sim' in args.backend: tag='fake_'+tag
        if args.provider=="local_sim":
            tag=args.backend.split('_')[1]
            if 'fake' in args.backend: tag='fake_'+tag
        md['short_name']='%s_%s'%(tag,md['hash'])
    else:
        myHN=hashlib.md5(os.urandom(32)).hexdigest()[:6]
        md['hash']=myHN
        md['short_name']=args.expName
    #print(args.backend); pprint(md);  aaa

#...!...!....................
def construct_random_inputs(md,verb=1, seed=None):
    pmd=md['payload']
    num_addr=pmd['num_addr']
    nq_data=pmd['nq_data']
    n_img=pmd['num_sample']
    
    # generate float random data
    np.random.seed(pmd['rnd_seed'])  # Set a fixed seed for reproducibility, None gives alwasy random 
    data_inp = np.random.uniform(-1, 1., size=(num_addr, nq_data, n_img))
    #print('data_inp sample:\n',data_inp[:3,:3,:2]); kk

    if pmd['cal_1M1']: # Fill the last image with alternating patterns
        magn = np.random.uniform(0.85, 0.95, size=(num_addr, nq_data))
        signs = np.random.choice([-1, 1], size=(num_addr, nq_data))
        # Combine signs and magnitudes
        data_inp[...,-1] = magn * signs
        
    if verb>2:
        print('input data.T=',data_inp.shape,repr(data_inp.T))
    bigD={'inp_udata': data_inp}
    return bigD


#...!...!....................
def harvest_sampler_results(job,md,bigD,T0=None):  # many circuits
    pmd=md['payload']
    qa={}
    jobRes=job.result()
    
    
    if T0!=None :  # when run locally
        elaT=time()-T0
        print(' job done, elaT=%.1f min'%(elaT/60.))
        qa['running_duration']=elaT
        qa['timestamp_running'] = '%.1g'%(elaT)
    else:
        try:
            jobMetr=job.metrics()
            #print('HSR:jobMetr:',jobMetr)
            #print('tt',jobMetr['timestamps']['running'])
            # Convert IBM UTC timestamp to PT
            t1=iso_to_pt_time((jobMetr['timestamps']['running']))
            qa['timestamp_running']=dateT2Str(t1)
            qa['quantum_seconds']=jobMetr['usage']['quantum_seconds']
        except:
            aa=1
            
    #1pprint(jobRes[0])
    nCirc=len(jobRes)  # number of circuit in the job
    jstat=str(job.status())
    
    countsL=[ jobRes[i].data.c.get_counts() for i in range(nCirc) ]
    #print('countsL:',countsL)
    # collect job performance info
    res0cl=jobRes[0].data.c
    qa['status']=jstat
    qa['num_circ']=nCirc
    qa['shots']=res0cl.num_shots
    
    qa['num_clbits']=res0cl.num_bits
    
    print('job QA'); pprint(qa)
    md['job_qa']=qa
    bigD['rec_udata'], bigD['rec_udata_err'] =  qcrank_reco_from_yields(countsL,pmd['nq_addr'],pmd['nq_data'])
    #print('rec2 data.T',bigD['rec_udata'].T)
    return bigD


#=================================
#=================================
#  M A I N 
#=================================
#=================================
if __name__ == "__main__":

    args=commandline_parser()
    
    np.set_printoptions(precision=3)
    expMD=buildPayloadMeta(args)
   
    pprint(expMD)
    expD=construct_random_inputs(expMD,args.verb)
    
    # generate parametric circuit
    nq_addr, nq_data = args.numQubits
    
    qcrankObj = QCrankV2( nq_addr, nq_data, useCZ=args.useCZ,measure=True,barrier=not args.noBarrier, mockCirc=args.mockCirc )
        
    qcP=qcrankObj.circuit
    cxDepth=qcP.depth(filter_function=lambda x: x.operation.name == 'cx')
    print('.... PARAMETRIZED IDEAL CIRCUIT .............., cx-depth=%d'%cxDepth)
    nqTot=qcP.num_qubits
    print('M: ideal gates count:', qcP.count_ops())
    if args.verb>2 or nq_addr+nq_data<7:  print(qcrankObj.circuit.draw())
      
    if args.exportQPY1:  M_export_qpy_parm(qcP) ; exit(0)
    if args.exportQPY2: M_export_qpy_bound();  exit(0)  # circuit is now corrupted
               
    
    # ------  construct sampler(.) job ------
    runLocal=True  # ideal or fake backend
    outPath=os.path.join(args.basePath,'meas') 
    if 'ideal' in args.backend:
        assert not args.useRC
        qcT=qcP
        transBackN='ideal'
        backend = AerSimulator()
    else:
        print('M: activate QiskitRuntimeService() ...')
        service = QiskitRuntimeService()
        if  'fake' in args.backend:
            assert not args.useRC
            transBackN=args.backend.replace('fake_','ibm_')
            hw_backend = service.backend(transBackN)
            backend = AerSimulator.from_backend(hw_backend) # overwrite ideal-backend
            print('fake noisy backend =', backend.name)
        else:
            outPath=os.path.join(args.basePath,'jobs')
            assert 'ibm' in args.backend
            assert  args.useRC  # always improves results
            backend = service.backend(args.backend)  # overwrite ideal-backend
            print('use true HW backend =', backend.name)          
            runLocal=False
        if 0:  # special case
            print('\nM: scan over transpiler  for %s :'%args.backend)            
            for i in range(10):
                seed=args.transpSeed+i
                qcT= transpile(qcP, backend=backend, optimization_level=3, seed_transpiler=seed)
                layout=qcT._layout.final_index_layout(filter_ancillas=True)
                print('seed=%d  qubits=%s '%(seed,layout))
            exit(0)

        qcT =  transpile(qcP, backend,optimization_level=3, seed_transpiler=args.transpSeed)
        qcrankObj.circuit=qcT  # pass transpiled parametric circuit back
        cxDepth=qcT.depth(filter_function=lambda x: x.operation.name == 'cz')
        print('.... PARAMETRIZED Transpiled (%s) CIRCUIT .............., cx-depth=%d'%(backend.name,cxDepth))
        print('M: transpiled gates count:', qcT.count_ops())
        if args.verb>2 or nq_addr+nq_data<7:  print(qcT.draw('text', idle_wires=False))
                
        
    circ_depth_aziz(qcP,'ideal')
    circ_depth_aziz(qcT,'transpiled')
    harvest_circ_transpMeta(qcT,expMD,backend.name)
    print('M: run on backend:',backend.name,outPath)
    assert os.path.exists(outPath)
   
    # -------- bind the data to parametrized circuit  -------
    qcrankObj.bind_data(expD['inp_udata'])
    
    # generate the instantiated circuits
    qcEL = qcrankObj.instantiate_circuits()
    nCirc=len(qcEL)
    if args.verb>2 :
        print(f'.... FIRST INSTANTIATED CIRCUIT .............. of {nCirc}')
        print(qcEL[0].draw('text', idle_wires=False))
        
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
    
    if expMD['submit']['random_compilation']: #  RC works only for real HW
        options.twirling.enable_gates = True
        options.twirling.enable_measure = True
        options.twirling.num_randomizations=60
        print('M: enabled RandComp')

    if expMD['submit']['dynamical_decoupling']: #  DD works only for real HW
        options.dynamical_decoupling.enable = True
        options.dynamical_decoupling.sequence_type = 'XX'
        options.dynamical_decoupling.extra_slack_distribution = 'middle'
        options.dynamical_decoupling.scheduling_method = 'alap'
        print('M: enabled DD')

    sampler = Sampler(mode=backend, options=options)
    T0=time()
    job = sampler.run(tuple(qcEL))
   
    harvest_submitMeta(job.job_id(),expMD,args)    
    if args.verb>1: pprint(expMD)
    
    if runLocal:
        harvest_sampler_results(job,expMD,expD,T0=T0)
        print('M: got results')
        #...... WRITE  MEAS OUTPUT .........
        outF=os.path.join(outPath,expMD['short_name']+'.meas.h5')
        write4_data_hdf5(expD,outF,expMD)
        print('\n  basePath=%s'%args.basePath)
        print('  ./postproc_qcrank.py  --basePath  $basePath  --expName   %s   -p a    -Y\n'%(expMD['short_name']))        
    else:
        #...... WRITE  SUBMIT OUTPUT .........
        outF=os.path.join(outPath,expMD['short_name']+'.ibm.h5')
        write4_data_hdf5(expD,outF,expMD)
        print('   ./retrieve_ibmq_job.py  --basePath  $basePath --expName   %s   \n'%(expMD['short_name'] ))



    
