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

def osh_tool(url, log_msg):
    path = tempfile.mkdtemp()
    out = "[]"
    try:
        repo = git.Repo.clone_from(url, path)
        log_msg += " Project cloned; "
        osh_metadata = subprocess.run(
            ["osh", "-qC", path, "check", "--report-json=/dev/stdout"],
            capture_output=True,
            text=True,
            check=True)
        log_msg += " Osh tool ran successfully;"
        out = short_output(osh_metadata.stdout.removeprefix("JObject"))
    except subprocess.CalledProcessError as e:
        log_msg += " Osh tool failed;"
    except git.exc.GitError as e:
        log_msg += " Project not cloned;"
    except Exception as e:
        log_msg += "❗Error occurred: "+ e +";"

    cleanup(path)
    return log_msg, out
