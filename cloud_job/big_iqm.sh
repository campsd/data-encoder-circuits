#!/bin/bash
set -u ;  # exit  if you try to use an uninitialized variable
set -e ;  #  bash exits if any statement returns a non-true return value


#stop-me

basePath="/dataVault2025/dataPaper_IQM_eval2"
nSamp=40
backN=sirius
backN=garnet
#./submit_iqm_job.py  --basePath  $basePath  --numQubits 4 3 --numSample 40 --numShot 20_000

echo bp=$basePath

# Define array of qubit configurations
nqa_nqd_conf=("2 2" "2 3" "3 2"  "3 3")

for config in "${nqa_nqd_conf[@]}"; do
    # Split the config into nqa and nqd
    read -r nqa nqd <<< "$config"
    
    # Set shots based on nqa value
    if [ "$nqa" -eq 2 ]; then
        shots=10
    elif [ "$nqa" -eq 3 ]; then
        shots=20
    elif [ "$nqa" -eq 4 ]; then
        shots=40
    else
        shots=5  # default fallback
    fi
    
    expName=qcr${nqa}a${nqd}d_${backN}
    echo 
    echo expName=$expName shots/k=$shots
    #./submit_iqm_job.py  --backend $backN --basePath  $basePath  --numQubits $nqa $nqd --numSample $nSamp --numShot ${shots}_000 --expName $expName -E ; continue

    ./retrieve_iqm_job.py  --basePath  $basePath  --expName $expName 
    ./postproc_qcrank.py  --basePath  $basePath  --expName  $expName  -p a b
   
    echo "dealt with job for ${nqa}+${nqd} qubits, shots=$shots"
    echo
   
done

echo all DONE
