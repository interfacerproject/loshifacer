import json
import requests
import toml
import base64
import os
import sys
import multiprocessing  as mp
import logging, logging.handlers

from zenroom import zencode_exec
from datetime import datetime
from queue import Queue
from dotenv import load_dotenv
from loshifacer.gqlQueries import CREATE_ASSET, QUERY_VARIABLES
from loshifacer.osh_tool import osh_tool

load_dotenv()
PATH_TO_RDF=os.environ["PATH_TO_RDF"]
USERNAME=os.environ["USERNAME"]
EDDSA=os.environ["EDDSA"]
AGENT=os.environ["AGENT"]
URL=os.environ["URL"]
LOCATIONID=os.environ["LOCATIONID"]

# zenflows-crypto contract for signature
contract = """
Scenario eddsa: sign a graph query
Given I have a 'base64' named 'gql'
Given I have a 'keyring'
# Fix Apollo's mingling with query string
When I remove spaces in 'gql'
and I compact ascii strings in 'gql'
When I create the eddsa signature of 'gql'
And I create the hash of 'gql'
Then print 'eddsa signature' as 'base64'
Then print 'gql' as 'base64'
Then print 'hash' as 'hex'
"""

def sign_request(query, variables, log_msg):
    body = {"query": query, "variables": variables}
    keys = {"keyring": {"eddsa": EDDSA}}
    data = {
        "gql": base64.b64encode(bytes(json.dumps(body), 'utf-8')).decode('utf-8')
    }
    result = zencode_exec(contract,
                          keys=json.dumps(keys),
                          data=json.dumps(data))
    if("ERROR" in result.logs):
        log_msg += " Zenroom signature error " + result.logs + ";"
        return log_msg, {}
    return log_msg, {
        "zenflows-sign": json.loads(result.output)["eddsa_signature"],
        "zenflows-user": USERNAME,
        "zenflows-hash": json.loads(result.output)["hash"]
    }

def ql(query, log_msg, variables={}, sign=False):
    request_headers = {}
    if sign:
        log_msg, request_headers = sign_request(query, variables, log_msg)
    result = requests.post(URL,
                           json={"query": query, "variables": variables},
                           headers=request_headers).json()
    if "errors" in result:
        log_msg += " GraphQL query error "+ result["errors"] + ";"
        return log_msg, {}
    return log_msg, result["data"]

def create_mutation(metadata, log_msg):
    log_msg, iv = ql(QUERY_VARIABLES, log_msg)
    spec = iv["instanceVariables"]["specs"]["specProjectDesign"]["id"]
    try:
        print("⚙️ processing " + metadata["name"])
        log_msg, asset = ql(
            query=CREATE_ASSET,
            log_msg=log_msg,
            variables={
                "name": metadata["name"],
                "note": metadata["function"],
                "okhv": metadata["okhv"],
                "version": metadata["version"],
                "repo": metadata["repo"],
                "license": metadata["license"],
                "licensor": metadata["licensor"] if isinstance(metadata["licensor"], str) else metadata["licensor"][0],
                "metadata": json.dumps(metadata),
                "resourceSpec": spec,
                "agent": AGENT,
                "location": LOCATIONID,
                "oneUnit": iv["instanceVariables"]["units"]["unitOne"]["id"],
                # WIP on the creationTime
                # different iso format between js and python
                "creationTime": datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            },
            sign=True
        )
        print('✅ ASSET CREATED for', metadata["name"], ":", asset)
        log_msg = "✅ " + log_msg
    except Exception as e:
        print('❌ ASSET NOT CREATED: '+e)
        log_msg = "❌ " + log_msg
    return log_msg

def worker_process(work_queue, log_queue):
    # logging
    h = logging.handlers.QueueHandler(log_queue)
    root = logging.getLogger()
    root.addHandler(h)
    root.setLevel(logging.INFO)
    # process
    while True:
        t = work_queue.get(True)
        if t is None:
            break
        t = toml.loads(t)
        log_msg = "🛠 work on " + t["name"] +";" # + mp.current_process().name +
        log_msg, t["osh_metadata"] = osh_tool(t["repo"], log_msg)
        log_msg = create_mutation(t, log_msg)
        innerlogger = logging.getLogger('worker')
        innerlogger.info(log_msg)
    print("🚨 ", mp.current_process().name, " has finished, quit")

def writer_process(start_path, queue, n_workers):
    for root, dirs, files in os.walk(start_path):
        for f in files:
            if f[-4:] == "toml":
                r = open(os.path.join(root, f), 'r')
                content = r.read()
                queue.put(content)
                r.close()
    for _ in range(n_workers):
        queue.put(None)

def listener_process(log_queue):
    root = logging.getLogger()
    file_handler = logging.handlers.RotatingFileHandler('ingestion.log', 'a', 10000, 1)
    formatter = logging.Formatter('%(asctime)s %(processName)-10s %(name)s %(levelname)-8s %(message)s')
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    root.setLevel(logging.INFO)
    while True:
        record = log_queue.get(True)
        if record is None:
            break
        logger = logging.getLogger(record.name)
        logger.handle(record)

def main():
    if( len(sys.argv) >0 ): initial_path=sys.argv[1]
    else: initial_path="RDF"
    start_path=PATH_TO_RDF+initial_path

    n_workers = mp.cpu_count() - 2
    work_queue = mp.Queue()
    log_queue = mp.Queue()

    writer = mp.Process(target=writer_process, args=(start_path, work_queue, n_workers))
    print("📖 started writer:   ", writer.name)
    writer.start()

    listener = mp.Process(target=listener_process, args=(log_queue,))
    print("📻 started listener: ", listener.name)
    listener.start()

    workers = [mp.Process(target=worker_process, args=(work_queue, log_queue,)) for _ in range(n_workers)]
    for w in workers:
        print("👷 started worker:   ", w.name)
        w.start()

    for w in workers:
        w.join()
    print('🔥 Ingestion done')
    log_queue.put(None)

if __name__=="__main__":
    main()