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
from PlotterQCrankV3 import Plotter

from toolbox.Util_QiskitV2 import unpack_numpy_to_counts

import argparse
def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--verbosity",type=int,choices=[0, 1, 2,3,4],  help="increase output verbosity", default=1, dest='verb')
    parser.add_argument("-p", "--showPlots",  default='a', nargs='+',help="abcd-string listing shown plots")
    
    parser.add_argument( "-Y","--noXterm", dest='noXterm',  action='store_false', default=True, help="enables X-term for interactive mode")         
    parser.add_argument("--basePath",default='out',help="head dir for set of experimentst")
                        
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
def postproc_qcrank(bigD,md):
    pom=md['postproc']
    #if pom['hw_calib']: expD['rec_udata']*=pom['ampl_fact']  # changes DATA
    rdata=expD['rec_udata'].flatten()
    tdata=expD['inp_udata'].flatten()

    elm=compute_ellipse(tdata,rdata)

    if 1:  # hack to do self-calibration
        expD['rec_udata']*=elm['ampl_fact']  # changes DATA
        rdata=expD['rec_udata'].flatten()
        tdata=expD['inp_udata'].flatten()
        pom['hw_calib']='auto'
        pom['ampl_fact']=elm['ampl_fact']
                
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
    pom['ellipse']=elm
    
#...!...!....................
def compute_ellipse(X: np.ndarray, Y: np.ndarray):
    # Stack X and Y into a 2D array
    data = np.vstack((X, Y)).T
    
    # Compute covariance matrix and eigenvalues
    cov_matrix = np.cov(data.T)
    eig_vals,  eig_vecs  = np.linalg.eig(cov_matrix)
    
    # Compute width and height
    width, height = 2 * np.sqrt(eig_vals[:2])
    angle_rad=np.arctan2(*eig_vecs[:, 0][::-1])
    if width <height :
        width, height=height,width
        angle_rad=angle_rad-np.pi/2
        #eig_vecs=np.flip(eig_vecs,axis=1)
        print('flipped')
    
    angle_deg=np.rad2deg(angle_rad)
    correlation = np.corrcoef(X,Y)[0, 1]
    amplFact=1/np.tan(angle_rad)
    # Print width and height
    print('Width: %.3f   Height: %.3f  ang=%.1f deg  correl=%.3f ampleFact=%.2f'%( width,height,angle_deg,correlation,amplFact))
    outD={'num_pix':X.shape[0],'width':width,'height':height,'angle':angle_rad, 'correl':correlation,'ampl_fact':amplFact}
    #pprint(outD)
    
    # from matplotlib.patches import Ellipse
    #ax.scatter(X,Y, alpha=0.5)
    #ellipse = Ellipse(xy=mean, width=width, height=height, angle=angle_deg, edgecolor='red', facecolor='none')
    return outD


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
    
    if args.verb>=2:
        print('M:expMD:');  pprint(expMD)
        if args.verb>=3:
            print(expD)
        stop2
        
    postproc_qcrank(expD,expMD)
      
    #...... WRITE  OUTPUT
    outF=os.path.join(args.outPath,expMD['short_name']+'.h5')
    write4_data_hdf5(expD,outF,expMD)

    
    #--------------------------------
    # ....  plotting ........
    args.prjName=expMD['short_name']
    expMD['plot']={'resid_max_range':0.3}

    plot=Plotter(args)
    fig0=10 if expMD['postproc']['hw_calib'] else 1
   
    if 'a' in args.showPlots:
        plot.ehands_accuracy(expD,expMD,figId=fig0)

    if 'c' in args.showPlots:
        not_tested
        plot.xyz()

    plot.display_all()
    print('M:done')
    #pprint(expMD) #tmp
