#!/bin/bash
set -u ;  # exit  if you try to use an uninitialized variable
set -e ;  #  bash exits if any statement returns a non-true return value

#  bash script which will execute this line 5x, changed execName to be _1, _2,...
#  It is used to overcome 10k shots/circuit limit at Qtuum - make sure to fix rndSeed so circuits can be averaged

#stop-me

basePath="/dataVault2025/paper_QCE2025_noisyH1"

echo bp=$basePath
nqa=3 ; nSamp=50; nqd=12 ; nj=3
nqa=4 ; nSamp=10; nqd=16 ; nj=5
#nqa=5 ; nSamp=20; nqd=10  ; nj=10

for i in {1..5}; do
    expName=qcr${nqa}a+${nqd}d_h1-1e_$i
    
    #./submit_qtuum_job.py --rndSeed 42 --basePath $basePath --numQubits ${nqa} $nqd --numSample $nSamp --numShot 10_000 --backend H1-1E --expName $expName -E  ; continue

    ./retrieve_qtuum_job.py  --basePath $basePath  --expName  $expName
    
    if [ $i -eq 1 ] ; then
	./postproc_qcrank.py  --basePath $basePath  --expName  $expName   -p a
    fi

    
    echo "dealt with  job $i "
    echo
done

./merge_shots.py --dataPath $basePath/meas --expName  qcr${nqa}a+${nqd}d_h1-1e_* --numJobs $nj
./postproc_qcrank.py --basePath $basePath  --expName  qcr${nqa}a+${nqd}d_h1-1e_1x$nj -p a

echo all DONE
