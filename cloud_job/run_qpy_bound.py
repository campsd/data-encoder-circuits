#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

"""
Load list of  quantum circuits from QPY files,run on fake backend, compare output w/ truth

Has build in QCrank decoder for simple case with 1 data qubit
Uses results from last circuit for auto-scaling

# Combine all arguments
./run_qpy_bound.py --input out/qcrank_nqa2_nqd2_bound.qpy --nshot 75000 --backendType 2

"""

import numpy as np
from qiskit import  transpile
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.fake_provider import FakeTorino, FakeCusco

from qiskit import qpy
import matplotlib.pyplot as plt
import os
import argparse

def plot_results(tdata, rdata, outF,backendName,txt):
    # Flatten arrays for plotting
    tdata_flat = tdata.flatten()
    rdata_flat = rdata.flatten()
    residuals = rdata_flat - tdata_flat
    
    # Create figure with 2 subplots
    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    
    # Left plot: correlation between rdata and tdata
    ax=axes[0]
    ax.scatter(tdata_flat, rdata_flat, alpha=0.5,s=10)
    ax.set_xlabel('tdata')
    ax.set_ylabel('rdata')
    ax.set_title('Correlation,  '+backendName)
    # Add 45-degree dashed line
    lims = [min(tdata_flat.min(), rdata_flat.min()), 
            max(tdata_flat.max(), rdata_flat.max())]
    ax.plot(lims, lims, 'k--', alpha=0.5, zorder=0)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3) 
    
    ax.text(0.05,0.8,txt,transform=ax.transAxes,color='r')
    
    # Right plot: histogram of residuals
    axes[1].hist(residuals, bins=30, alpha=0.7) 
    axes[1].set_xlabel('Residuals')
    axes[1].set_ylabel('Frequency')
    axes[1].set_title('Residuals Distribution')
    # Add vertical line at y=0 (x=0 in this context since residuals are on x-axis)
    axes[1].axvline(x=0, color='r', linestyle='--', linewidth=2)
    # Calculate and display mean & std
    mean_res = np.mean(residuals)
    std_res = np.std(residuals)
    ndata=tdata_flat.shape[0]
    axes[1].text(0.05, 0.95, f'nData: {ndata}\nMean: {mean_res:.4f}\nStd: {std_res:.4f}',
                 transform=axes[1].transAxes, verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xlim(-0.3,0.3)
    
    plt.tight_layout()
    
    plt.savefig(outF)
    print(f'\nSaved plot: {outF}')
    
    plt.show()

    
def post_process(countsL,qcL,nshot):
    nCirc=len(qcL)
    for ic in range(nCirc):
        qcM=qcL[ic].metadata
        nq_addr=qcM["nq_addr"]
        nq_data=qcM["nq_data"]
        tdata=np.array(qcM["inp_data"])
        counts=countsL[ic]
        seq_len=1<<nq_addr
        pr=ic==0 or ic==nCirc-1
        if pr:
            print('\npost ic',ic)
            print('tdata',tdata)
        assert nq_data==1  # hardcoded in decoding below
        assert seq_len==tdata.shape[0]  # sanity check
        if ic==0:
            tAll=np.zeros((nCirc,seq_len))
            rAll=np.zeros_like(tAll)
        #print('counts:',len(counts),counts)
        
        probs=counts        
        rdata=np.zeros(seq_len) # tmp storage
        fstr='0'+str(nq_addr)+'b' 
        for j in range(seq_len):
            mbit=format(j,fstr)
            mbit0=mbit+'0'; mbit1=mbit+'1'
            m1=probs[mbit1] if mbit1 in probs else 0
            m0=probs[mbit0] if mbit0 in probs else 0
            m01=m0+m1
            if m01>0 :
                p=m1/m01
            else: 
                p=0
            rdata[j]=1-2*p
        if pr: print('rdata:', rdata)
        tAll[ic]=tdata
        rAll[ic]=rdata 
    return tAll,rAll

def auto_scale(tdata,rdata):
    tcdata=tdata[-1]
    rcdata=rdata[-1]
    facV=rcdata/tcdata
    ampFac=1/np.mean(facV)
    print('cal_1M1',ampFac)
    #return tdata, rdata *ampFac  # will include also calibration circuits
    # ... drop last circuit &  rescale the rest
    tdata=tdata[:-1]
    rdata=rdata[:-1]  *ampFac
    return tdata, rdata,ampFac

def get_parser():
    parser = argparse.ArgumentParser(
        description='Run quantum circuits from QPY files on fake backends',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument('-i','--input', type=str, default='out/qcrank_nqa4_nqd1_bound.qpy',
                        help='Input QPY file path')
    parser.add_argument('-n','--nshot', type=int, default=50_000,
                        help='Number of shots for circuit execution')
    parser.add_argument('-b','--backendType', type=int, default=0, choices=[0, 1, 2],
                        help='Backend type: 0=ideal (AerSimulator), 1=FakeTorino, 2=FakeCusco')
    
    return parser

def main(args):
    inpF = args.input
    nshot = args.nshot
    
    print('simu :',inpF)
    with open(inpF, 'rb') as fd:
        qcL=qpy.load(fd)

    qc=qcL[0]
    print('circ0:',qc.metadata['name'])
    print(qc)
    print( 'ideal ops:',qc.count_ops())

    # Select backend based on backendType argument
    if args.backendType == 0:
        backend = AerSimulator()  # perfect performance
        print('Backend: AerSimulator (ideal)')
    elif args.backendType == 1:
        backend = FakeTorino()  # medium performance
        print('Backend: FakeTorino')
    elif args.backendType == 2:
        backend = FakeCusco()  # poor performance
        print('Backend: FakeCusco')

    qcT = transpile(qcL, backend=backend, optimization_level=3, seed_transpiler=42)
    print(backend.name, 'ops:',qcT[0].count_ops())

    # Run the transpiled circuit using the chosen backend
    job = backend.run(qcT, shots=nshot)
    counts = job.result().get_counts()
    #print(backend.name,'Counts:',counts)

    tdata,rdata=post_process(counts,qcL,nshot)
    tdata,rdata,ampFac=auto_scale(tdata,rdata)

    txt='amp Fac=%.2f \nseq_len=%d\nnshot=%d'%(ampFac,tdata.shape[1],nshot)
    outF = inpF.replace('.qpy', '_b%d.png'%args.backendType)
    plot_results(tdata, rdata, outF,backend.name,txt)

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    main(args)

