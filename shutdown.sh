counter=0
port=0

while [ $counter -lt 64 ]
do
    ((port = 8000 + counter))
    curl http://localhost:${port}/shutdown
    ((counter++))
    ((counter++))
done

echo All done
