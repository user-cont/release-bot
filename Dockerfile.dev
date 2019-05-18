FROM registry.fedoraproject.org/fedora:30

EXPOSE 8080

ENV STI_SCRIPTS_URL=image:///usr/libexec/s2i \
    STI_SCRIPTS_PATH=/usr/libexec/s2i \
    # The $HOME is not set by default, but some applications needs this variable
    HOME=/opt/app-root/src \
    PATH=/opt/app-root/src/bin:/opt/app-root/bin:/opt/app-root/src/.local/bin:$PATH

LABEL summary="Automated releasing from GitHub repositories" \
      name="release-bot" \
      description="Automated releasing from GitHub repositories" \
      io.k8s.description="Automated releasing from GitHub repositories" \
      io.k8s.display-name="Release Bot" \
      io.openshift.tags="builder" \
      io.openshift.s2i.scripts-url="$STI_SCRIPTS_URL" \
      usage="s2i build <CONFIGURATION-REPOSITORY> usercont/release-bot:dev <APP-NAME>"

RUN dnf install -y git nss_wrapper

RUN mkdir -p ${HOME} && \
    useradd -u 1001 -r -g 0 -d ${HOME} -s /sbin/nologin \
    -c "Default Application User" default && \
    chown -R 1001:0 /opt/app-root

USER 1001

RUN git clone https://github.com/user-cont/release-bot.git $HOME/release-bot && \
    pip3 install --user $HOME/release-bot/ && \
    chgrp -R 0 /opt/app-root && \
    chmod -R g=u /opt/app-root

# S2I scripts
COPY ./.s2i-dev/bin/  $STI_SCRIPTS_PATH

WORKDIR $HOME

CMD $STI_SCRIPTS_PATH/usage
