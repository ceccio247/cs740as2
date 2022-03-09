counter=0
while [ $counter -lt 64 ]
do
    python3 chord.py $counter &
    ((counter++))
    ((counter++))
done


echo All done
