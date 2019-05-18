FROM registry.fedoraproject.org/fedora:30

RUN dnf install -y git make

ENV HOME=/home/test-user \
    PYTHONDONTWRITEBYTECODE=1

RUN useradd -u 1000 -d ${HOME} test-user

WORKDIR ${HOME}

COPY requirements.txt ${HOME}/
COPY tests/requirements.txt ${HOME}/tests/
RUN pip3 install -r requirements.txt -r tests/requirements.txt

COPY Makefile ${HOME}/

COPY ./tests/ ${HOME}/tests/
RUN chown -R 1000 ${HOME}

COPY . /tmp/tmp/
RUN cd /tmp/tmp/ && pip3 install . && rm -rf /tmp/tmp/

USER 1000

CMD make test
