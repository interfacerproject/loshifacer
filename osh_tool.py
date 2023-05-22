import subprocess
import tempfile
import errno
import shutil
import json
import git
from datetime import datetime

common_error = "File-format issue(s)"

def cleanup(path):
    try:
        shutil.rmtree(path)
    except OSError as exc:
        if exc.errno != errno.ENOENT:  # ENOENT - no such file or directory
            raise

def with_execution_date(data):
    data["execution_date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return data

def short_output(data):
    output = {}
    js = json.loads(data)
    output["prelude"] = js["prelude"]
    output["stats"] = js["stats"]
    output["checks"] = []

    for item in js["checks"]:
        out = {}
        out["name"] = item["name"]
        out["passed"] = item["passed"]
        out["state"] = item["state"]
        if not item["passed"]:
            out["issues"] = []
            if item["name"] in ["Clean CAD files", "Clean electronics files"]:
                issues = set([])
                o = {}
                o["severity"] = item["issues"][0]["severity"]
                for issue in item["issues"]:
                    msg = issue["msg"].split(":", 2)
                    issues.update(msg[1].split(","))
                o["msg"] = common_error + ":" + ",".join(issues)
                out["issues"].append(o)
            else:
                for issue in item["issues"]:
                    o = {}
                    o["severity"] = issue["severity"]
                    msg = issue["msg"].split(":", 2)
                    o["msg"] = msg[0]
                    out["issues"].append(o)
        output["checks"].append(out)
    return output

def osh_tool(url):
    path = tempfile.mkdtemp()
    out = "[]"
    try:
        repo = git.Repo.clone_from(url, path, recursive=True)
        print("\033[1;32m Project cloned: "+url+"\033[0;0m")
        osh_metadata = subprocess.run(
            ["./osh", "-qC", path, "check", "--report-json=/dev/stdout"],
            capture_output=True,
            text=True,
            check=True)
        print("\033[1;32m Osh tool ran successfully on: "+url+"\033[0;0m")
        out = short_output(osh_metadata.stdout.removeprefix("JObject"))
    except subprocess.CalledProcessError as e:
        print("\033[1;31m Osh tool error on: "+url+"\033[0;0m")
    except git.exc.GitError as e:
        print("\033[1;31m Project not cloned: "+url+"\033[0;0m")
    except Exception as e:
        print("\033[1;31m ❗Error: "+e+"\033[0;0m")

    cleanup(path)
    return with_execution_data(out)