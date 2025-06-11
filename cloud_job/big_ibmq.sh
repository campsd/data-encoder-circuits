#!/bin/bash
set -u ;  # exit  if you try to use an uninitialized variable
set -e ;  #  bash exits if any statement returns a non-true return value


#stop-me

basePath="/dataVault2025/dataPaper_IQM_eval2"
nSamp=40
transpSeed=42
backN=aachen
backN=marrakesh
#backN=ideal

echo bp=$basePath

declare -A mitCase0=(
    ["raw"]=" "
    ["RC"]="--useRC"
    ["RCDD"]="--useRC --useDD"
)
declare -A mitCase=(
    ["raw"]=" "
    ["RC"]="--useRC"
)
# Define array of qubit configurations
nqa_nqd_conf=("2 2" "2 3" "3 2"  "3 3" "4 4" "5 5")
#nqa_nqd_conf=("3 3")

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
    elif [ "$nqa" -eq 5 ]; then
        shots=80
    else
        shots=5  # default fallback
    fi
    
    for tag1 in "${!mitCase[@]}"; do
        
        opt1="${mitCase[$tag1]}"
        echo "name=$tag1  task=$opt1"

        expName=qcr${nqa}a${nqd}d_${backN}_${tag1}
        echo 
        echo expName=$expName shots/k=$shots
        #!./submit_ibmq_job.py  --backend ibm_$backN --basePath  $basePath  --numQubits $nqa $nqd --numSample $nSamp --numShot ${shots}_000 --expName $expName -E --transpSeed $transpSeed  $opt1  ; continue

        ./retrieve_ibmq_job.py  --basePath  $basePath  --expName $expName 
        ./postproc_qcrank.py  --basePath  $basePath  --expName  $expName  -p a b
       
        echo "dealt with job for ${nqa}+${nqd} qubits, shots=$shots"
        echo
        
    done  # Close the inner loop for tag1
done  # Close the outer loop for config

echo all DONE
