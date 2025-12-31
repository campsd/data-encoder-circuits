#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

import os, sys

from toolbox.Util_H5io4 import  write4_data_hdf5, read4_data_hdf5

from pprint import pprint
import numpy as np

from matplotlib.ticker import MaxNLocator

from matplotlib.gridspec import GridSpec
from toolbox.PlotterBackbone import PlotterBackbone
class Stump:
    a=1

#............................
#............................
#............................
class Plotter(PlotterBackbone):
    def __init__(self, args):
        PlotterBackbone.__init__(self,args)

#...!...!..................
    def scanResidual(self,dataD,tag=1,figId=1):
        figId=self.smart_append(figId)        
        nrow,ncol=1,1 
        fig=self.plt.figure(figId,facecolor='white', figsize=(8,5.5))
        ax = self.plt.subplot(nrow,ncol,1)

        mkD={'ideal':['o',12,'k','Ideal simu 1k shots/address'],
             'forte-1':['D',10,'r',"IonQ Forte-1 w/ debias Oct'25"],
             'pittsburgh':['P',12,'b',"IBM Pittsburgh w/ RC Oct'25"] }

        if tag==1:
            jSort=3; xLab='input capacity  (sequence length)'; tit='QCrank accuracy vs. input size'
            lloc='upper left'
        if tag==2:
            jSort=8; xLab='num CZ gates (after transpilation)'; tit='QCrank accuracy vs. used CZ gates'
            lloc='upper center'
        tit+=', fig=%d'%figId

        for back in dataD:
            xV=np.array(dataD[back]['data'])
            mk,ms,mc,dLab=mkD[back]
            # Sort xV by column jSort
            sort_indices = np.argsort(xV[:, jSort])
            xV = xV[sort_indices]
            print('SRL: ',back,mk,jSort,xV.shape)
            #print('xV:',xV)
            #print(xV[:,jSort],xV[:,6]); exit(0)
            ax.errorbar(xV[:,jSort],xV[:,5],yerr=xV[:,6], marker=mk,label=dLab,color=mc, markerfacecolor='none', markersize=ms)
                  
        legend =ax.legend(loc=lloc,title='Backend')

        ax.set(xlabel=xLab,ylabel='Inaccuracy (RMSE)',title=tit)
        ax.set_ylim(0.0,)
        if self.venue=='paper': return
        ax.grid()

#...!...!..................
    def IbmCountCZ(self, dataD, qpu='pittsburgh', figId=3):
        figId=self.smart_append(figId)
        nrow,ncol=1,1
        fig=self.plt.figure(figId, facecolor='white', figsize=(6,5))
        ax = self.plt.subplot(nrow,ncol,1)
        
        # Get data for specified QPU
        xV = np.array(dataD[qpu]['data'])
        
        # Sort by x-value (column 3: inp size)
        jSort = 3
        sort_indices = np.argsort(xV[:, jSort])
        xV = xV[sort_indices]
        
        # Extract data for plotting
        x_data = xV[:, 3]  # inp size (input capacity)
        y_data = xV[:, 8]  # CZ gates
        addr_qubits = xV[:, 1].astype(int)  # addr qubits
        data_qubits = xV[:, 2].astype(int)  # data qubits
        
        # Create log-log plot (markers only, no lines)
        ax.plot(x_data, y_data, 'o', color='b', markersize=8, label=qpu)
        
        # Add text annotations for each point
        for i in range(len(x_data)):
            label_text = '%d-%d' % (addr_qubits[i], data_qubits[i])
            ax.text(x_data[i], y_data[i], label_text, fontsize=12, 
                   ha='left', va='bottom', color='red')
        
        # Add explanation text for label format
        ax.text(0.5, 0.1, 'Labels: nq_addr - nq_data', 
               transform=ax.transAxes, fontsize=10, color='red',
               verticalalignment='top')
        
        # Add dashed line y=3*x
        x_range = np.array([x_data.min(), x_data.max()])
        y_line = 3 * x_range
        ax.plot(x_range, y_line, 'k--', linewidth=1.5, alpha=0.7, label='y = 3x')
        
        # Set log-log scale
        ax.set_xscale('log')
        ax.set_yscale('log')
        
        # Set explicit tick positions and labels (no exponents)
        x_ticks = [20, 30, 40, 50, 60, 80, 100, 150]
        y_ticks = [50, 100, 200, 300, 400, 500]
        
        ax.set_xticks(x_ticks)
        ax.set_xticklabels([str(t) for t in x_ticks])
        ax.set_yticks(y_ticks)
        ax.set_yticklabels([str(t) for t in y_ticks])
        
        # Disable minor ticks
        ax.minorticks_off()
        
        # Labels and title
        ax.set_xlabel('input capacity (sequence length)')
        ax.set_ylabel('num CZ gates')
        ax.set_title('CZ gate count, QCrank - %s, fig=%d'%(qpu,figId))
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left')

#...!...!..................
    def attenFact(self, dataD, figId=4):
        figId=self.smart_append(figId)
        nrow,ncol=1,1
        fig=self.plt.figure(figId, facecolor='white', figsize=(8,5.5))
        ax = self.plt.subplot(nrow,ncol,1)
        
        mkD={'ideal':['o',12,'k','Ideal simu'],
             'forte-1':['D',10,'r','IonQ Forte-1 w/ debias'],
             'pittsburgh':['P',12,'b','IBM Pittsburgh w/ RC'] }
        
        jX = 3  # inp size (input capacity)
        jY = 7  # atten factor
        
        for back in dataD:
            xV = np.array(dataD[back]['data'])
            mk, ms, mc, dLab = mkD[back]
            
            # Sort by x-value
            sort_indices = np.argsort(xV[:, jX])
            xV = xV[sort_indices]
            
            x_data = xV[:, jX]  # input capacity
            y_data = xV[:, jY]  # attenuation factor
            
            ax.plot(x_data, y_data, marker=mk, label=dLab, color=mc, 
                   markerfacecolor='none', markersize=ms, linestyle='-')
        
        ax.legend(loc='upper left', title='Backend')
        ax.set_xlabel('input capacity (sequence length)')
        ax.set_ylabel('attenuation factor')
        ax.set_title('Attenuation factor, QCrank, fig=%d'%figId)
        ax.axhline(y=1.0, color='gray', linestyle='--', linewidth=1, alpha=0.7)
        ax.set_ylim(0.9,)
        ax.grid(True, alpha=0.3)


def load_csv_data1(inpFile):
    # Initialize with empty dicts for each QPU
    dataD = {'ideal': {}, 'forte-1': {}, 'pittsburgh': {}}
    
    # Temporary lists to collect rows for each QPU
    temp_data = {'ideal': [], 'forte-1': [], 'pittsburgh': []}
    
    with open(inpFile, 'r') as f:
        lines = f.readlines()
    print('lines:', len(lines), 'inpFile:', inpFile)
    
    # Parse header (first line) and drop last 4 columns
    header = lines[0].strip().split(',')
    header = [h.strip() for h in header[:-4]]  # Drop last 4 columns
    print('header columns:', header)
    
    # Columns C-K are indices 2-10 (9 columns)
    keys = header[2:11]  # 'total qubits' through 'CZ gates'
    
    # Process data lines
    for line in lines[1:]:
        # Strip whitespace
        line = line.strip()
        
        # Skip empty lines, lines starting with #, or lines with just commas
        if not line or line.startswith('#') or line.replace(',', '').strip() == '':
            continue
        #print('line:', line)
        
        # Split by comma
        parts = line.split(',')
        
        # Check if this is a valid data line
        if len(parts) < len(header):
            continue
        
        # Drop last 4 columns (keep same number as header)
        parts = parts[:len(header)]
        
        qpu = parts[0].strip()
        
        # Skip if QPU is not one of the expected values
        if qpu not in dataD:
            continue
        #print('qpu:', qpu)
        
        # Store method from first record for this QPU
        if 'method' not in dataD[qpu]:
            dataD[qpu]['method'] = parts[1].strip()
        
        # Extract numerical values from columns C-K (indices 2-10)
        try:
            row_values = []
            for i in range(2, 11):  # Columns C-K
                value = parts[i].strip()
                # Remove quotes and comma separators from numeric values
                value = value.replace('"', '').replace(',', '')
                
                if value == '':
                    row_values.append(np.nan)
                else:
                    try:
                        # Try float conversion (handles both int and float)
                        row_values.append(float(value))
                    except ValueError:
                        # If conversion fails, use NaN
                        row_values.append(np.nan)
            
            # Add row to temporary data
            temp_data[qpu].append(row_values)
            
        except (ValueError, IndexError) as e:
            print(f'Skipping invalid line: {e}')
            continue
    
    # Convert lists to numpy arrays and finalize structure
    print('data keys:',keys)
    for qpu in dataD.keys():
        dataD[qpu]['keys'] = keys
        if temp_data[qpu]:
            dataD[qpu]['data'] = np.array(temp_data[qpu])
        else:
            dataD[qpu]['data'] = np.array([]).reshape(0, len(keys))
        print('qpu:', qpu, 'data:', dataD[qpu]['data'].shape)
    
    return dataD
    
#=================================
#=================================
#  M A I N 
#=================================
#=================================
if __name__=="__main__":

    inpData='data/2025_11.ionq_ibm.csv'
    outPath='out/'
  
    dataD=load_csv_data1(inpData)
    #print('dataD:');    pprint(dataD)

    args=Stump()
    args.prjName='figA_IonQ'
    args.noXterm=True
    args.verb=1
    # args.formatVenue='paper'
    args.outPath=outPath
 
    # ----  just plotting
    plot=Plotter(args)
    plot.scanResidual(dataD,tag=1)
    plot.scanResidual(dataD,tag=2)
    plot.IbmCountCZ(dataD, qpu='pittsburgh')
    plot.attenFact(dataD)
    
    plot.display_all(png=1)
    print('M:done')
