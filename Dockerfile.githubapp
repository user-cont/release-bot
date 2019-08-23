FROM registry.fedoraproject.org/fedora:30

ENV LANG=en_US.UTF-8
# nicer output from the playbook run
ENV ANSIBLE_STDOUT_CALLBACK=debug
# Ansible doesn't like /tmp
COPY files/ /src/files/

USER 0

RUN mkdir /home/release-bot && chmod 0776 /home/release-bot
COPY files/passwd /home/release-bot/passwd
ENV LD_PRELOAD=libnss_wrapper.so
ENV NSS_WRAPPER_PASSWD=/home/release-bot/passwd
ENV NSS_WRAPPER_GROUP=/etc/group

# Install packages first and reuse the cache as much as possible
RUN dnf install -y ansible \
    && cd /src/ \
    && ansible-playbook -vv -c local -i localhost, files/install-rpm-packages.yaml \
    && dnf clean all

COPY setup.py setup.cfg requirements.txt files/recipe.yaml /src/
# setuptools-scm
COPY .git /src/.git
COPY release_bot/ /src/release_bot/

RUN cd /src/ \
    && ansible-playbook -vv -c local -i localhost, files/recipe.yaml


USER 1001
ENV USER=release-bot
ENV HOME=/home/release-bot

CMD ["release-bot -c /home/release-bot/.config/conf.yaml"]