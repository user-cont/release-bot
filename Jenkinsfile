def test-suite

def onmyduffynode(script){
    ansiColor('xterm'){
        timestamps{
            sh 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -l root ${DUFFY_NODE}.ci.centos.org -t \"export REPO=${REPO}; export BRANCH=${BRANCH};\" "' + script + '"'
        }
    }
}

test-suite = {
    stage("Release-bot test") {
        try{
            stage ("Allocate node"){
                env.CICO_API_KEY = readFile("${env.HOME}/duffy.key").trim()
                duffy_rtn=sh(
                            script: "cico --debug node get -a ${arch} -f value -c hostname -c comment",
                            returnStdout: true
                            ).trim().tokenize(' ')
                env.DUFFY_NODE=duffy_rtn[0]
                env.DUFFY_SSID=duffy_rtn[1]
            }

            stage ("setup"){
                    onmyduffynode "yum -y install docker make"
            }

            stage("build test image"){
                onmyduffynode "make test-image"
            }

            stage("run test suite inside the container"){
                onmyduffynode "make test-in-container"
            }

        } catch (e) {
            currentBuild.result = "FAILURE"
            throw e
        } finally {
            stage("Cleanup"){
                sh 'cico node done ${env.SSID}'
            }
        }
    }
}



node('slave06.ci.centos.org'){

    stage('Checkout'){
        checkout scm
    }

    stage('Build'){
        test-suite
    }
}