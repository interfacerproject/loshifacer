import json
import requests
import toml
import base64
import gitlab

from zenroom import zencode_exec
from datetime import datetime
from gqlQueries import CREATE_ASSET, QUERY_VARIABLES
from osh_tool import osh_tool
from threading import Thread, current_thread
from queue import Queue

# zenflows testing credential
username = "matteo"
EdDSA = '2dYy36i7e34uMtzVu8i2NHfzPwpW89RQayWJtub7Urio'
agent = '061KFE1AADXNDYTXRYTG007A14'
url = "http://65.109.11.42:9000/api"

# gitlab references for rdf
gl = gitlab.Gitlab('https://gitlab.opensourceecology.de')
project = gl.projects.get('verein/projekte/losh-rdf')

# queue
q = Queue()

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

def sign_request(query, variables):
    body = {"query": query, "variables": variables}
    keys = {"keyring": {"eddsa": EdDSA}}
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
        "zenflows-user": username,
        "zenflows-hash": json.loads(result.output)["hash"]
    }

def ql(query, variables={}, sign=False):
    request_headers = {}
    if sign:
        request_headers = sign_request(query, variables)
    result = requests.post(url,
                           json={"query": query, "variables": variables},
                           headers=request_headers).json();
    if "errors" in result:
        print(result["errors"])
        raise SystemExit('GraphQL query error')
    return result["data"];

def create_mutation(metadata):
    iv = ql(QUERY_VARIABLES)
    spec = iv["instanceVariables"]["specs"]["specProjectDesign"]["id"]
    locationId = "061KFEJCA035RE8TSAYDN6DVDC"
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
                "agent": agent,
                "location": locationId,
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

def worker():
    while True:
        t = q.get()
        print("🛠 ", current_thread().name, " working on ", t["name"])
        t["osh_metadata"] = osh_tool(t["repo"])
        create_mutation(t)
        q.task_done()

def start_worker(number_of_workers):
    for i in range(number_of_workers):
        print("🏃 worker ", (i+1), " started")
        thread = Thread(target=worker, name="worker "+str(i+1))
        thread.deamon = True
        thread.start()

def start_ingestion(start_folder):
    items = project.repository_tree(path=start_folder, iterator=True)
    for item in items:
        if item["type"] == "tree":
            start_ingestion(item["path"])
        elif item["name"][-4:] == "toml":
            f = project.files.get(file_path=item["path"], ref='main')
            content = base64.b64decode(f.content).decode('utf-8')
            t = toml.loads(content)
            q.put(t)

def main(start_folder, number_of_workers):
    start_worker(number_of_workers)
    start_ingestion(start_folder)

if __name__=="__main__":
    main('RDF', 10)
    
