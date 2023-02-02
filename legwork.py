import json
import requests
import toml
import base64
import os

from zenroom import zencode_exec
from datetime import datetime
from gqlQueries import CREATE_ASSET, QUERY_VARIABLES
from osh_tool import osh_tool
from queue import Queue
from dotenv import load_dotenv
import multiprocessing  as mp

load_dotenv()
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

oversize_note = 0

def sign_request(query, variables):
    body = {"query": query, "variables": variables}
    keys = {"keyring": {"eddsa": EDDSA}}
    data = {
        "gql": base64.b64encode(bytes(json.dumps(body), 'utf-8')).decode('utf-8')
    }
    result = zencode_exec(contract,
                          keys=json.dumps(keys),
                          data=json.dumps(data))
    if("ERROR" in result.logs):
        print(result.logs)
        raise SystemExit('Zenroom error')
    return {
        "zenflows-sign": json.loads(result.output)["eddsa_signature"],
        "zenflows-user": USERNAME,
        "zenflows-hash": json.loads(result.output)["hash"]
    }

def ql(query, variables={}, sign=False):
    request_headers = {}
    if sign:
        request_headers = sign_request(query, variables)
    result = requests.post(URL,
                           json={"query": query, "variables": variables},
                           headers=request_headers).json()
    if "errors" in result:
        print(result["errors"])
        raise SystemExit('GraphQL query error')
    return result["data"]

def create_mutation(metadata):
    iv = ql(QUERY_VARIABLES)
    spec = iv["instanceVariables"]["specs"]["specProjectDesign"]["id"]
    if len(metadata["function"]) > 2048:
        global oversize_note
        oversize_note += 1
        return
    try:
        print("⚙️ processing " + metadata["name"])
        asset = ql(
            query=CREATE_ASSET,
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
    except Exception as e:
        print(e)

def ingestion(queue):
    while True:
        t = queue.get(True)
        if t is None:
            break
        t = toml.loads(t)
        print("🛠 ", mp.current_process().name, " working on ", t["name"])
        t["osh_metadata"] = osh_tool(t["repo"])
        create_mutation(t)
    print("🚨 ", mp.current_process().name, " has finished, quit")

def rdf_parsing(start_path, queue, n_workers):
    for root, dirs, files in os.walk(start_path):
        for f in files:
            if f[-4:] == "toml":
                r = open(os.path.join(root, f), 'r')
                content = r.read()
                queue.put(content)
                r.close()
    for _ in range(n_workers):
        queue.put(None)

def main(start_path):
    n_workers = mp.cpu_count() - 1
    queue = mp.Queue()

    workers = [mp.Process(target=ingestion, args=(queue,)) for _ in range(n_workers)]
    for w in workers:
        print("👷 started worker: ", w.name)
        w.start()

    writer = mp.Process(target=rdf_parsing, args=(start_path, queue, n_workers))
    writer.start()

    for w in workers:
        w.join()
    print('🔥 Ingestion done')
    print('project skipped for notes too big: ', oversize_note)

if __name__=="__main__":
    main('../losh-rdf/RDF/github.com')