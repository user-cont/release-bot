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
      io.k8s.display-name="Ruby 2.4" \
      io.openshift.expose-services="8080:http" \
      io.openshift.tags="builder,ruby,ruby24,rh-ruby24" \
      io.openshift.s2i.scripts-url="$STI_SCRIPTS_URL" \
      usage="s2i build <SOURCE-REPOSITORY> release-bot <APP-NAME>"

RUN dnf install -y python3 python2 python-pip fedpkg git

RUN mkdir -p ${HOME} && \
	useradd -u 1001 -r -g 0 -d ${HOME} -s /sbin/nologin \
    -c "Default Application User" default && \
  	chown -R 1001:0 /opt/app-root

USER 1001

RUN pip3 install --user release-bot && \
    pip install --user wheel

# S2I scripts
COPY ./.s2i/bin/  $STI_SCRIPTS_PATH

WORKDIR $HOME

CMD release-bot --help