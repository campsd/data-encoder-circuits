#!/bin/bash
set -u ;  # exit  if you try to use an uninitialized variable
set -e ;  #  bash exits if any statement returns a non-true return value

#  bash script which will execute this line 5x, changed execName to be _1, _2,...
#  It is used to overcome 10k shots/circuit limit at Qtuum - make sure to fix rndSeed so circuits can be averaged

stop-me

basePath="/dataVault2025/paper_QCE2025_noisyH1"

echo bp=$basePath
nqd=12

for i in {2..5}; do
    expName=qcr4a+${nqd}d_h1-1e_$i
    
    #./submit_qtuum_job.py --rndSeed 42 --basePath $basePath --numQubits 4 $nqd --numSample 50 --numShot 10_000 --backend H1-1E --expName $expName -E

    ./retrieve_qtuum_job.py  --basePath $basePath  --expName  $expName

    ./postproc_qcrank.py  --basePath $basePath  --expName  $expName   -p a
    echo "dealt with  job $i "
    echo
done
