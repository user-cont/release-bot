def test_targets = ["test_bot.py", "test_changelog.py", "test_fedora.py", "test_github.py", "test_load_release_conf.py", "test_pypi.py", "test_specfile.py"]
def tests = [:]

def onmyduffynode(script){
    ansiColor('xterm'){
        timestamps{
            sh 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -l root ${DUFFY_NODE}.ci.centos.org -t \"export REPO=${REPO}; export BRANCH=${BRANCH};\" "' + script + '"'
        }
    }
}

def synctoduffynode(source)
{
    sh 'scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -r ' + source + " " + "root@" + "${DUFFY_NODE}.ci.centos.org:~/"
}

node('userspace-containerization'){

    stage('Checkout'){
        checkout scm
    }

    stage('Build'){
        try{
            stage ("Allocate node"){
                env.CICO_API_KEY = readFile("${env.HOME}/duffy.key").trim()
                duffy_rtn=sh(
                            script: "cico --debug node get --arch x86_64 -f value -c hostname -c comment",
                            returnStdout: true
                            ).trim().tokenize(' ')
                env.DUFFY_NODE=duffy_rtn[0]
                env.DUFFY_SSID=duffy_rtn[1]
            }

            stage ("setup"){
                onmyduffynode "yum -y install docker make"
                synctoduffynode "*" // copy all source files
                onmyduffynode "systemctl start docker"
            }

            stage("build test image"){
                onmyduffynode "make image-test"
            }

            stage("Run test suite in parallel") {
                test_targets.each { test_target ->
                    tests["$test_target"] = {
                        stage("Test target: $test_target"){
                            onmyduffynode "docker run -v /root:/usr/src/app:Z -e GITHUB_USER= -e GITHUB_TOKEN= release-bot-tests make test TEST_TARGET=tests/$test_target"
                        }
                    }
                }

                parallel tests
            }
        } catch (e) {
            currentBuild.result = "FAILURE"
            throw e
        } finally {
            stage("Cleanup"){
                sh 'cico node done ${DUFFY_SSID}'
            }
        }
    }
}
