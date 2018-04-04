FROM registry.fedoraproject.org/fedora:27

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
      usage="s2i build <SOURCE-REPOSITORY> koscicz/release-bot <APP-NAME>"

RUN dnf install -y python3 python2 python-pip fedpkg git krb5-workstation

RUN mkdir -p ${HOME} && \
	useradd -u 1001 -r -g 0 -d ${HOME} -s /sbin/nologin \
    -c "Default Application User" default && \
  	chown -R 1001:0 /opt/app-root && \
  	sed 's/default_ccache_name/#default_ccache_name/g' /etc/krb5.conf > /etc/krb5.conf

USER 1001

RUN pip install --user wheel PyYaml && \
    git clone https://github.com/kosciCZ/release-bot.git $HOME/release-bot && \
    pip3 install --user -r $HOME/release-bot/requirements.txt && \
    chgrp -R 0 /opt/app-root && \
    chmod -R g=u /opt/app-root

# S2I scripts
COPY ./.s2i-dev/bin/  $STI_SCRIPTS_PATH

WORKDIR $HOME

CMD $STI_SCRIPTS_PATH/usage
