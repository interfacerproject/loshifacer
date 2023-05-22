ARG OKH_TOOL_VER=0.4.4
ARG PROJVAR_VER=0.16.2
ARG MLE_VER=0.23.0
ARG OSH_DIR_STD_VER=0.7.0
ARG OSH_TOOL_VER=0.4.0

FROM dyne/devuan:chimaera as okh-tool
WORKDIR /app/tmp
ARG OKH_TOOL_VER
RUN wget -qO- -- \
		"https://github.com/OPEN-NEXT/LOSH-OKH-tool/releases/download/$OKH_TOOL_VER/okh-tool-$OKH_TOOL_VER-x86_64-unknown-linux-musl.tar.gz" \
	| tar -xzf -
RUN  mv -- "okh-tool-$OKH_TOOL_VER-x86_64-unknown-linux-musl/okh-tool" ..


FROM dyne/devuan:chimaera AS projvar
WORKDIR /app/tmp
ARG PROJVAR_VER
RUN wget -qO- -- \
		"https://github.com/hoijui/projvar/releases/download/$PROJVAR_VER/projvar-$PROJVAR_VER-x86_64-unknown-linux-musl.tar.gz" \
	| tar -xzf -
RUN  mv -- "projvar-$PROJVAR_VER-x86_64-unknown-linux-musl/projvar" ..


FROM dyne/devuan:chimaera AS mle
WORKDIR /app/tmp
ARG MLE_VER
RUN wget -qO- -- \
		"https://github.com/hoijui/mle/releases/download/$MLE_VER/mle-$MLE_VER-x86_64-unknown-linux-musl.tar.gz" \
	| tar -xzf -
RUN mv -- "mle-$MLE_VER-x86_64-unknown-linux-musl/mle" ..


FROM dyne/devuan:chimaera AS osh-dir-std
WORKDIR /app/tmp
ARG OSH_DIR_STD_VER
RUN wget -qO- -- \
		"https://github.com/hoijui/osh-dir-std-rs/releases/download/$OSH_DIR_STD_VER/osh-dir-std-$OSH_DIR_STD_VER-x86_64-unknown-linux-musl.tar.gz" \
	| tar -xzf -
RUN mv -- "osh-dir-std-$OSH_DIR_STD_VER-x86_64-unknown-linux-musl/osh-dir-std" ..

FROM alpine AS osh-tool
RUN apk --no-cache add git nim nimble gcc musl-dev pcre-dev openssl1.1-compat-libs-static
WORKDIR /app/tmp
ARG OSH_TOOL_VER
RUN git clone -q --depth 1 --recurse-submodules -b "$OSH_TOOL_VER" \
	https://github.com/hoijui/osh-tool .
RUN nimble build -y \
	-d:release \
	--opt:speed \
	--passL:-static \
	--passL:-no-pie \
	-d:usePcreHeader \
	--passL:-lpcre \
	--dynlibOverride:ssl \
	--passL:-lssl \
	--dynlibOverride:crypto \
	--passL:-lcrypto
RUN mv build/osh ..

FROM python:3.8-bullseye
RUN apt install -y git gcc make libffi-dev
RUN pip install poetry

ARG USER=zosh
ARG GROUP=$USER

ARG PATH_TO_RDF=/var/losh-rdf
ENV PATH_TO_RDF=$PATH_TO_RDF
ARG USERNAME=losh
ENV USERNAME=$USERNAME

# RUN addgroup -S -- "$GROUP"
# RUN adduser -SG "$GROUP" -- "$USER"

WORKDIR /app

COPY --from=okh-tool --chown=$USER:$GROUP /app/okh-tool ./bin/
COPY --from=projvar --chown=$USER:$GROUP /app/projvar ./bin/
COPY --from=mle --chown=$USER:$GROUP /app/mle ./bin/
COPY --from=osh-dir-std --chown=$USER:$GROUP /app/osh-dir-std ./bin/
COPY --from=osh-tool --chown=$USER:$GROUP /app/osh ./bin/

ENV PATH=$PATH:/app/bin

COPY pyproject.toml ./
COPY loshifacer/* ./loshifacer/

RUN poetry install

VOLUME /var/losh-rdf
VOLUME /tmp

# RUN git clone https://gitlab.opensourceecology.de/verein/projekte/losh-rdf /var/losh-rdf
# RUN cd /var/losh-rdf && git reset --hard HEAD~1

# USER $USER:$GROUP

CMD [ "poetry", "run", "cronjob"  ]

