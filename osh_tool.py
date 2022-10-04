import subprocess
import tempfile
import errno
import shutil
import json
import git

common_error = "File-format issue(s)"

def cleanup(path):
    try:
        shutil.rmtree(path)
    except OSError as exc:
        if exc.errno != errno.ENOENT:  # ENOENT - no such file or directory
            raise

def short_output(data):
    output = []

    # data contains some DEBUG strings and can contain an extra comma
    # at the end of the json
    s = '\n'.join(line for line in data.split('\n') if 'DEBUG' not in line)
    if s[-4] == ",":
        s = s[:-4]+"\n]\n"
    js = json.loads(s)
    
    for item in js:
        out = {}
        out["name"] = item["name"]
        out["passed"] = item["passed"]
        out["state"] = item["state"]
        if item["passed"] == "false":
            out["issues"] = []
            if item["name"] in ["Clean CAD files", "Clean electronics files"]:
                issues = set([])
                o = {}
                o["importance"] = item["issues"][0]["importance"]
                for issue in item["issues"]:
                    if o["importance"] != issue["importance"]:
                        print(o["importance"])
                        print(issue["importance"])
                        raise
                    msg = issue["msg"].split(":", 2)
                    issues.update(msg[1].split(","))
                o["msg"] = common_error + ":" + ",".join(issues)
                out["issues"].append(o)
            else:
                for issue in item["issues"]:
                    o = {}
                    o["importance"] = issue["importance"]
                    msg = issue["msg"].split(":", 2)
                    o["msg"] = msg[0]
                    out["issues"].append(o)
        output.append(out)
    return output

def osh_tool(url):
    path = tempfile.mkdtemp()
    try:
        repo = git.Repo.clone_from(url, path, depth=1)
        # print("\033[1;32m Cloned project: "+url+"\033[0;0m")
    except Exception as e:
        # print("\033[1;31m Project not cloned: "+url+"\033[0;0m")
        cleanup(path)
        return "[]"
    osh_metadata = subprocess.run(
        ["./osh", "-C", path, "check", "--json"],
        stdout=subprocess.PIPE,
        text=True)
    cleanup(path)
    return short_output(osh_metadata.stdout)
