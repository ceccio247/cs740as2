
curl http://localhost:8000/init_alone

sleep 2

counter=2
port=0

while [ $counter -lt 64 ]
do
    ((port=8000+counter))
    curl http://localhost:${port}/init?other=0
    ((counter++))
    ((counter++))
    sleep 1
done
