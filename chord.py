import warnings
warnings.simplefilter("ignore", UserWarning)

from flask import Flask
from flask import request
import os
import logging
import sys
import hashlib
import requests


#logging.getLogger('werkzeug').disabled = True
#os.environ['WERKZEUG_RUN_MAIN'] = 'true'

app = Flask(__name__)

# the constant m for this chord setup
# to have a good number of chord nodes we set m=6 for 64 possible identifiers

M = 4

# the identifier for this node
# must be in the range [0,(2^m)-1]
node_id = 0

# the predecessor of this node
predecessor = -2

# finger table
# we note that in the paper the finger table is indexed from 1
# for clarity of code we also index this table from 1
finger = [-1] * (M+1)


# whether we have initialized this node
initialized = False



def closest_preceding_finger(identifier):
    # go from M to 1
    for i in range(M, 0, -1):
        if(in_modulus_range(finger[i], node_id, identifier)):
            return finger[i]
    return node_id


def in_modulus_range(identifier, start, end):
    # ranges in modulus spaces are normal except when they 'cross over' zero
    # this is a helper function that deals with that egde case
    # this function tests if identifier is within (start,end)

    if (start <= end):
        # normal range stuff
        return ((identifier > start) and (identifier < end))
    else:
        # this range crosses over zero
        # we split it into two ranges:
        # (start, (2^m)-1] and [0, end)
        return (((identifier > start) and (identifier <= ((2**M)-1))) or
                ((identifier >= 0) and (identifier < end)))


def find_predecessor(identifier):
    curr_id = node_id
    while ((not in_modulus_range(identifier,
                            curr_id,
                            (get_successor(curr_id)+1)%(2**M)))
                            and (curr_id != get_successor(curr_id))):
        curr_id = get_closest_preceding_finger(curr_id, identifier)
    return curr_id


def find_successor(identifier):
    pred_id = find_predecessor(identifier)
    return get_successor(pred_id)

def update_others():
    return
    for i in range(1,M+1):
        p = find_predecessor((node_id - (2**(i-1)))%(2**M))
        send_update_finger_table(p, node_id, i)

def init_finger_table(other_node):
    finger[1] = get_find_successor(other_node, node_id)
    global predecessor
    predecessor = get_predecessor(finger[1])
    send_set_predecessor(finger[1], node_id)

    for i in range(1, M):
        current_finger_start = (node_id+(2**(i-1)))%(2**M)
        next_finger_start = (node_id+(2**i))%(2**M)

        if in_modulus_range(next_finger_start,
                            (node_id-1)%(2**M),
                            current_finger_start):
            finger[i+1] = finger[i]
        else:
            finger[i+1] = get_find_successor(other_node, next_finger_start)


def update_finger_predicate(s, index):
    # what we really want to know is "is s closer to us than finger[i]"?
    # we also have to take care of the case where finger[i]=n
    # because that means finger[i] is 2**M away from us, NOT 0 away
    finger_dist = (finger[index] - node_id) % (2**M)
    if finger_dist == 0:
        finger_dist = 2**M
    new_dist = (s - node_id) % (2**M)
    print(node_id)
    print(s)
    print(finger[index])

    print(new_dist)
    print(finger_dist)
    return (new_dist < finger_dist)

def update_finger_table(s, index):
    print("PING")
    if(update_finger_predicate(s, index)):
        finger[index] = s
        p = predecessor
        send_update_finger_table(p, s, index)






def get_predecessor(identifier):
    # request the node with id 'identifier' to return its predecessor
    if identifier == node_id:
        return predecessor

    port = 8000 + identifier
    print('getting pred of ' + str(identifier))
    r = requests.get('http://localhost:' + str(port) + '/predecessor')
    print('get_pred result from ' + str(identifier) + ' = ' + str(r.json()['predecessor']))
    return r.json()['predecessor']

def get_successor(identifier):
    # request the node with id 'identifier' to return its successor
    if identifier == node_id:
        return finger[1]

    port = 8000 + identifier
    print('getting suc of ' + str(identifier))
    r = requests.get('http://localhost:' + str(port) + '/successor')
    return int(r.json()['successor'])

def get_closest_preceding_finger(identifier, target_id):
    if identifier == node_id:
        return closest_preceding_finger(target_id)

    port = 8000 + identifier
    print('getting closest_prec of ' + str(identifier))
    r = requests.get('http://localhost:' + str(port) + '/closest_preceding_finger' + 
                    '?id=' + str(target_id))
    return r.json()['finger']

def get_find_successor(identifier, target_id):
    # runs 'find successor' on the node 'identifier'
    if identifier == node_id:
        return find_successor(target_id)

    port = 8000+identifier
    print('getting find successor of ' + str(identifier))
    r = requests.get('http://localhost:' + str(port) + '/find_successor' + 
                    '?id=' + str(target_id))
    return r.json()['successor']
    

def send_update_finger_table(identifier, target_id, index):
    print('updating finger table of ' + str(identifier))
    if identifier == node_id:
        update_finger_table(target_id, index)
        return

    port = 8000+identifier
    r = requests.get('http://localhost:' + str(port) + '/update_finger_table' +
                    '?s=' + str(target_id) + '&index=' + str(index))

def send_set_predecessor(identifier, target_id):
    if identifier == node_id:
        global predecessor
        predecessor = target_id
        return

    print('updating pred of ' + str(identifier) + " to " + str(target_id))
    port = 8000+identifier
    r = requests.get('http://localhost:' + str(port) + '/set_predecessor' +
                    '?id=' + str(target_id))






@app.route('/closest_preceding_finger')
def closest_preceding_finger_helper():
    identifier = ''
    try:
        identifier = int(request.args.get('id'))
    except:
        return {'message': 'You must provide a valid id'}
    
    return {'finger': closest_preceding_finger(identifier)}


@app.route('/find_successor')
def find_successor_helper():
    identifier = ''
    try:
        identifier = int(request.args.get('id'))
    except:
        return {'message': 'You must provide a valid id'}
    
    return {'successor': find_successor(identifier)}


@app.route('/lookup')
def key_lookup():
    key = ''
    try:
        key = request.args.get('key')
    except:
        return 'You must provide a key'
    key_id = int(hashlib.sha1(key.encode("utf-8")).hexdigest(),16) % (2**M)

    # now that we have the id, we perform the find_successor function
    # as described in figure 4 of the paper
    return {'responsible_node': find_successor(key_id)}

@app.route('/update_finger_table')
def update_finger_table_helper():
    s = ''
    try:
        s = int(request.args.get('s'))
    except:
        return {'message': 'You must provide a valid id'}
    
    index = ''
    try:
        index = int(request.args.get('index'))
    except:
        return {'message': 'You must provide a valid index'}
    update_finger_table(s, index)
    return {'message': 'done'}


@app.route('/hello')
def hello():
    return 'Hello, World! My identifier is ' + str(node_id)

@app.route('/dump_fingers')
def dunp_fingers():
    return {'fingers': finger}


@app.route('/predecessor')
def return_predecessor():
    return {'predecessor': predecessor}

@app.route('/set_predecessor')
def set_predecessor():
    global predecessor
    
    identifier = ''
    try:
        identifier = int(request.args.get('id'))
    except:
        return {'message': 'You must provide a valid id'}

    if ((identifier < 0) or (identifier > ((2**M)-1))):
        return {'message': 'You must provide a valid id'}

    predecessor = identifier
    return {'predecessor': predecessor}

@app.route('/successor')
def return_successor():
    return {'successor': finger[1]}
        

@app.route('/init')
def init_with_other():
    global initialized
    if initialized:
        return {'message': 'node already initialized'}
    
    other = ''
    try:
        other = int(request.args.get('other'))
    except:
        return {'message': 'You must provide a valid id'}
    
    if ((other < 0) or (other > ((2**M)-1))):
        return {'message': "ERROR: Other node identifier is not in the range [0,(2^m)-1]"}

    init_finger_table(other)
    update_others()

    initialized = True

    return {'message': 'init complete'}

@app.route('/init_alone')
def init_alone():
    global predecessor
    global initialized

    if initialized:
        return {'message': 'node already initialized'}

    for i in range(1,M+1):
        finger[i] = node_id        
    predecessor = node_id
    
    initialized = True

    return {'message': 'init complete'}

# utility for gracefully shutting down a flask server running in the background
# taken from http://web.archive.org/web/20190706125149/http://flask.pocoo.org/snippets/67
def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route('/shutdown')
def shutdown():
    shutdown_server()
    return 'Server shutting down...'

if __name__ == "__main__":
    # retrieve this node's identifier from the command line
    if (len(sys.argv) != 2):
        print("ERROR: Incorrect usage")
        print("Usage is chord.py <identifier>")
        quit()

    try:
        node_id = int(sys.argv[1])
    except:
        print("ERROR: Identifier could not be converted to integer")
        quit()
    
    if ((node_id < 0) or (node_id > ((2**M)-1))):
        print("ERROR: Identifier is not in the range [0,(2^m)-1]")
        quit()


    # in normal chord, id is not linked to the address of the node
    # but for the sake of simplicity, we run each node on a port based on id
    # this could easily be changed to have the chord nodes run on arbitrary ports
    # and have each node's finger tables include the address of each node
    # they reference
    # this has not been done out of convenience
    port = 8000+node_id

    app.run(host="localhost", port=port, debug=True, use_reloader=False)
