FROM python:3.7
ENV PYTHONUNBUFFERED=1

RUN mkdir /opt/scoreengine2
WORKDIR /opt/scoreengine2

RUN apt-get update && apt-get install -y libsasl2-dev libldap2-dev libssl-dev

RUN pip install --no-cache-dir --trusted-host pypi.python.org pipenv
COPY Pipfile .
COPY Pipfile.lock .
RUN pipenv sync

COPY . .

ENTRYPOINT ["pipenv", "run", "python", "scoreenginecli.py"]
