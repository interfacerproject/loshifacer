import os
import git
from shutil import copy, rmtree
from dotenv import load_dotenv
from codecs import escape_decode
from loshifacer.legwork import start as start_ingestion

load_dotenv()
PATH_TO_RDF = os.environ["PATH_TO_RDF"]

dir_scan = "to_be_scanned"

def cp_parents(file, target_dir):
    final_path = os.path.join(target_dir, file)
    final_dir = os.path.dirname(final_path)
    if not os.path.isdir(final_dir):
        os.makedirs(final_dir)
    copy(file, final_path)

def ingestion_needed():
    repo = git.Repo(PATH_TO_RDF)
    old_sha = repo.head.commit
    repo.remotes.origin.pull()
    if old_sha == repo.head.commit:
        return False
    files = repo.git.diff(old_sha, name_only=True)
    # move in RDF directory
    cwd = os.getcwd()
    os.chdir(PATH_TO_RDF)
    for f in iter(files.splitlines()):
        # resolves octal encoding
        if f.startswith("\""):
            f = escape_decode(f[1:-1])[0].decode("utf8")
        cp_parents(f, dir_scan)
    os.chdir(cwd)
    return True

def clone_losh_rdf():
    losh_dir = os.path.join(PATH_TO_RDF, '.git')
    if not os.path.isdir(losh_dir):
        repo = git.Repo.clone_from('https://gitlab.opensourceecology.de/verein/projekte/losh-rdf.git', PATH_TO_RDF)
        print("losh-rdf repository cloned")
    else:
        print("losh-rdf repository found")

def main():
    clone_losh_rdf()
    if ingestion_needed():
        print("Start ingestion")
        target_dir = os.path.join(PATH_TO_RDF, dir_scan)
        start_ingestion(target_dir)
        rmtree(target_dir)
    else:
        print("Nothing new in: " + PATH_TO_RDF)

if __name__ == "__main__":
    main()