#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

'''
Analyze  polyEH  experiment

'''

import os
from toolbox.Util_H5io4 import  write4_data_hdf5, read4_data_hdf5
from time import time
from pprint import pprint
import numpy as np
from PlotterQCrankV2 import Plotter

from toolbox.Util_QiskitV2 import unpack_numpy_to_counts

import argparse
def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--verbosity",type=int,choices=[0, 1, 2,3,4],  help="increase output verbosity", default=1, dest='verb')
    parser.add_argument("-p", "--showPlots",  default='a', nargs='+',help="abcd-string listing shown plots")
    
    parser.add_argument( "-Y","--noXterm", dest='noXterm',  action='store_false', default=True, help="enables X-term for interactive mode")         
    parser.add_argument("--basePath",default='out',help="head dir for set of experimentst")
    parser.add_argument("-N","--noAutoCalib", action='store_true', default=False, help="disable automatic self-calibration")
    parser.add_argument("--onlyCalibSamp", action='store_true', default=False, help="show only calibration data")
                        
    parser.add_argument('-e',"--expName",  default='exp_62a21daf',help='IBMQ experiment name assigned during submission')
    
    args = parser.parse_args()
    # make arguments  more flexible 
    args.dataPath=os.path.join(args.basePath,'meas')
    args.outPath=os.path.join(args.basePath,'post')
    args.showPlots=''.join(args.showPlots)
  
    
    print( 'myArg-program:',parser.prog)
    for arg in vars(args):  print( 'myArg:',arg, getattr(args, arg))
    
    assert os.path.exists(args.dataPath)
    assert os.path.exists(args.outPath)
    return args


#...!...!....................
def postproc_qcrank(bigD,md,doAutoCalib=True):
    pom=md['postproc']
    pmd=md['payload']
    if pmd['cal_1M1']:  # use last circuit for auto-calib
        rcdata=expD['rec_udata'][...,-1].flatten()
        tcdata=expD['inp_udata'][...,-1].flatten()
        facV=rcdata/tcdata
        ampFac=1/np.mean(facV)
        print('cal_1M1',ampFac)
        if not args.onlyCalibSamp: # clip last circuit from payload
            expD['rec_udata']=expD['rec_udata'][...,:-1]
            expD['inp_udata']=expD['inp_udata'][...,:-1]
        else:
            expD['rec_udata']=expD['rec_udata'][...,-1:]
            expD['inp_udata']=expD['inp_udata'][...,-1:]
               
    rdata=expD['rec_udata'].flatten()
    tdata=expD['inp_udata'].flatten()

    pom['only_calib_samp']=args.onlyCalibSamp
    if doAutoCalib:  # do self-calibration
        if md['payload']['cal_1M1']:            
            pom['hw_calib']='1M1'
            pom['ampl_fact']=ampFac
        else:
            pom['hw_calib']='auto??'
            pom['ampl_fact']=1. # tmp
        
        expD['rec_udata']*=pom['ampl_fact']  # changes DATA
        rdata=expD['rec_udata'].flatten()
        tdata=expD['inp_udata'].flatten()
    else:   
        pom['hw_calib']='off'
        pom['ampl_fact']=1.
        
    res_data = rdata - tdata
    mean = np.mean(res_data)
    std = np.std(res_data)
    # assuming normal distribution, compute std error of std estimator
    # SE_s=std/sqrt(2(n-1)), where n is number of samples
    N=res_data.shape[0]
    se_s=std/np.sqrt(2*(N-1))
    
    pom['res_mean']=float(mean)
    pom['res_std']=float(std)
    pom['res_SE_s']=float(se_s)
    #pom['ellipse']=elm
    

#=================================
#=================================
#  M A I N 
#=================================
#=================================
if __name__=="__main__":
    args=get_parser()
    np.set_printoptions(precision=3)
                    
    inpF=args.expName+'.meas.h5'
    expD,expMD=read4_data_hdf5(os.path.join(args.dataPath,inpF))

    if 0: # fix old code
        expMD['job_qa']['timestamp_running']=execTimeConverter(parsed_data)       
        
    if args.verb>=2:
        print('M:expMD:');  pprint(expMD)
        if args.verb>=3:
            print(expD)
        stop2
    
    # logic for  auto-calibration
    if expMD['payload']['num_sample']==1 and  expMD['payload']['cal_1M1']:
        assert args.onlyCalibSamp 
    doAutoCalib = not args.noAutoCalib  # apply it by default
    if args.verb>=1:
        print('M: auto-calibration:', 'enabled' if doAutoCalib else 'disabled')
        
    postproc_qcrank(expD,expMD,doAutoCalib=doAutoCalib)
      
    #...... WRITE  OUTPUT
    outF=os.path.join(args.outPath,expMD['short_name']+'.h5')
    write4_data_hdf5(expD,outF,expMD)

    
    #--------------------------------
    # ....  plotting ........
    args.prjName=expMD['short_name']
    expMD['plot']={'resid_max_range':0.3}

    plot=Plotter(args)
    fig0=1 if expMD['postproc']['hw_calib']=='off' else 10
    if args.onlyCalibSamp: fig0+=20
   
    if 'a' in args.showPlots:
        plot.ehands_accuracy(expD,expMD,figId=fig0)
    if 'b' in args.showPlots:
        plot.ehands_accuracy(expD,expMD,figId=fig0,asCol=True)

    if 'c' in args.showPlots:
        not_tested
        plot.xyz()

    plot.display_all()
    print('M:done')
    #pprint(expMD) #tmp
