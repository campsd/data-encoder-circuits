__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

from toolbox.PlotterBackbone import PlotterBackbone
from matplotlib import cm as cmap
import matplotlib.ticker as ticker
from pprint import pprint
import numpy as np
import matplotlib.gridspec as gridspec

from matplotlib.colors import LinearSegmentedColormap


#...!...!....................
def compute_correlation_and_draw_line(ax, x_data, y_data,xLR=[]):
    """Compute correlation and draw a line at the angle of correlation."""
    correlation = np.corrcoef(x_data, y_data)[0, 1]

    # Line representing correlation - slope based on correlation
    # y = mx + c, where m is the correlation coefficient
    # We pass through the mean of the points for the line of best fit
    mean_x, mean_y = np.mean(x_data), np.mean(y_data)
    ax.plot(mean_x,mean_y,'Dr',ms=5)
    m = correlation * np.std(y_data) / np.std(x_data)
    c = mean_y - m * mean_x
    
    # Points for the line
    x12 = np.array([min(x_data), max(x_data)])
    y12 = m * x12 + c
    ax.plot(x12, y12, 'r--',lw=1.0)

    th=np.arctan(m)
    txt='correl: %.2f,   theta %.0f deg'%(correlation,th/np.pi*180)
    ax.text(0.05,0.92,txt,transform=ax.transAxes,color='r')    
    
    ax.grid(True)
    return 

        
#...!...!....................
def plot_histogram(ax, res_data):
    """Plot histogram of the difference and annotate mean and std."""
    
    ax.hist(res_data, bins=25, color='salmon', alpha=0.7)
    mean = np.mean(res_data)
    std = np.std(res_data)
    # assuming normal distribution, compute std error of std estimator
    # SE_s=std/sqrt(2(n-1)), where n is number of samples
    N=res_data.shape[0]
    se_s=std/np.sqrt(2*(N-1))
    ax.axvline(mean, color='r', linestyle='dashed', linewidth=1)
    txt='Mean: %.3f\nStd: %0.3f +/- %0.3f'%(mean,std,se_s)
    ax.annotate(txt, xy=(0.05, 0.85),c='r', xycoords='axes fraction')
    ax.xaxis.set_major_locator(ticker.MaxNLocator(4))


#...!...!....................
def summary_column(md):
    #pprint(md)
    pmd=md['payload']
    smd=md['submit']
    tmd=md['transpile']
    pom=md['postproc']
    txt=md['short_name']
    txt+='\nback: %s'%smd['backend']
    txt+='\nshots/addr : %d'%(smd['num_shots']/pmd['num_addr'])
    txt+='\nshots/img : %d k'%(smd['num_shots']/1000)
    txt+='\nnum sample %d'%(pmd['num_sample'])
    txt+='\nsample size: %d'%(pmd['seq_len'])
    txt+='\nnum addr: %d'%pmd['num_addr']
    txt+='\nqubits: %d'%pmd['num_qubit']
    if 'ibm' in smd['backend']:  txt+='  RC: %r'%smd['random_compilation']
    txt+='\nnum 2q gates: %d'%tmd['2q_gate_count']
    txt+='\n2q gates depth: %d'%tmd['2q_gate_depth']

    #txt+='\nhwCalib: %s'%pom['hw_calib']
    #if pom['hw_calib']: txt+=' fac: %.2f'%pom['ampl_fact']
    return txt
    if 'noise_model' in smd:
        txt+='\nfake : %s'%(smd['noise_model'])       
 
   
  
#............................
#............................
#............................
class Plotter(PlotterBackbone):
    def __init__(self, args):
        PlotterBackbone.__init__(self,args)
        
#...!...!..................
    def ehands_accuracy(self,bigD,md,figId=1):
        #pprint(md)
        pmd=md['payload']
        smd=md['submit']
        tmd=md['transpile']
        if 'truth_rangeLR' in md:
            xrL,xrR=md['truth_rangeLR']
        else:
            xrL,xrR=-1.15, 1.15

        resMX=md['plot']['resid_max_range']
        
        figId=self.smart_append(figId)        
        nrow,ncol=1,3
        fig=self.plt.figure(figId,facecolor='white', figsize=(12,3*nrow))
        
        topTit=[ 'job: '+md['short_name'], 'Residual ',smd['backend']]

        
        #....... plot data .....
        rdata=bigD['rec_udata'].flatten()
        tdata=bigD['inp_udata'].flatten()
        #....  left column ....
        ax = self.plt.subplot(nrow,ncol,1)
           
        ax.scatter(tdata,rdata,alpha=0.6,s=4)
        ax.set(xlabel='true value',ylabel='reco')
        compute_correlation_and_draw_line(ax, tdata, rdata)
        ax.set_aspect(1.)
        ax.set_xlim(xrL,xrR);ax.set_ylim(xrL,xrR)
        x12 = np.array([min(tdata), max(tdata)])
        ax.plot(x12,x12,ls='--',c='k',lw=0.7)           
        ax.set_title(topTit[0]) 

        #..... right column ....
        ax = self.plt.subplot(nrow,ncol,3)
        res_data = rdata - tdata
        h = ax.hist2d(rdata, res_data, bins=20, cmap='Blues',cmin=0.1)
        self.plt.colorbar(h[3], ax=ax)

        compute_correlation_and_draw_line(ax, rdata , res_data) 
        ax.axhline(0.,ls='--',c='k',lw=1.0)

        ax.set_ylabel('reco-true')
        ax.set(xlabel='reco value',ylabel='reco-true')
        ax.set_title(topTit[1])

        ax.set_xlim(xrL,xrR); ax.set_ylim(-resMX,resMX)
        ax.grid()
        if 'ibm' in smd['backend']: 
            txt='phys:%s'%(tmd['phys_qubits'])
            ax.text(0.05, 0.1, txt, fontsize=10, color='m', ha='left', va='top',transform=ax.transAxes)
 
        #..... middle column ....
        ax = self.plt.subplot(nrow,ncol,2) 
        plot_histogram(ax,  res_data)
        ax.set_title(topTit[2])
        xLab= 'reco-true'
        ax.set(xlabel=xLab,ylabel='num pixels')
        ax.axvline(0.,ls='--',c='k',lw=1.0)
        ax.set_xlim(-resMX,resMX)
        
        # .... decorations ....
        # Overlay the text on top of the plots
        txt=summary_column(md)
        ax.text(0.88, 0.95, txt, fontsize=10, color='m', ha='left', va='top',transform=ax.transAxes)

#...!...!..................
    def xyz(self,bigD,md,figId=3):
        #pprint(md)
        pmd=md['payload']
        smd=md['submit']
        tmd=md['transpile']

        figId=self.smart_append(figId)        
        nrow,ncol=1,2
        fig=self.plt.figure(figId,facecolor='white', figsize=(12,4))

        make_it_work
