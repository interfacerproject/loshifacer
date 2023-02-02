#!/bin/bash

check_executable() {
    command -v $1 > /dev/null || {
	    >&2 echo "$1 executable missing"; exit 1
    }
}

check_executable git
check_executable nimble

echo "Installing osh-tool..."
rm -f osh
tmp=`mktemp -d`
git clone --recurse-submodules https://github.com/hoijui/osh-tool ${tmp}
cd ${tmp} && nimble build -y && cd - && cp ${tmp}/build/osh .
rm -rf ${tmp}

echo "Installing projvar..."
rm -f projvar
tmp=`mktemp -d`
wget -O ${tmp}/projvar.tgz -q https://github.com/hoijui/projvar/releases/download/0.16.0/projvar-0.16.0-x86_64-unknown-linux-musl.tar.gz
cd ${tmp} && tar -xzf projvar.tgz >/dev/null 2>&1 \
    && cd - && mv ${tmp}/projvar-*-x86_64-unknown-linux-musl/projvar .
rm -rf ${tmp}
export PATH=$PATH:${PWD}

echo ""
echo "End of preparation"