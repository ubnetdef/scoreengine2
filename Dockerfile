FROM python:3.7
ENV PYTHONUNBUFFERED=1

RUN mkdir /opt/scoreengine2
WORKDIR /opt/scoreengine2

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libldap2-dev \
        libsasl2-dev \
        libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY setup.py .

RUN pip install --no-cache-dir --trusted-host pypi.python.org --editable .

COPY . .

USER nobody

ENTRYPOINT ["scoreengine2"]
