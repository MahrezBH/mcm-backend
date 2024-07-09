pipeline {
    agent any

    environment {
        SERVER_IP = '65.21.108.31'
        SERVER_USER = 'root'
        GIT_REPO = 'git@github.com:MahrezBH/mcm-backend.git'
        BACKEND_DIR = '/root/mcm-backend'
        NEXUS_URL = 'http://37.27.4.176:8082/ilef/'
        NEXUS_REPO = 'ilef'
        NEXUS_CREDENTIALS_ID = 'nexus-credentials'
        DOCKER_IMAGE = 'mcm-backend'
        VERSION_FILE = '/root/version.txt'
        DOCKERFILE_DIR = 'ilef_cloud'
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out code...'
                git url: "${GIT_REPO}", branch: 'main'
            }
        }

        stage('Read and Update Version') {
            steps {
                script {
                    sshagent (credentials: ['APP-JENKINS-SSH']) {
                        sh """
                        ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} '
                            if [ ! -f ${VERSION_FILE} ]; then echo "0" > ${VERSION_FILE}; fi
                            version=\$(cat ${VERSION_FILE})
                            newVersion=\$((version + 1))
                            echo \$newVersion > ${VERSION_FILE}
                        '
                        """
                        def newVersion = sh(script: "ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} 'cat ${VERSION_FILE}'", returnStdout: true).trim()
                        env.DOCKER_TAG = newVersion
                        echo "New Docker tag: ${env.DOCKER_TAG}"
                    }
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                echo 'Building Docker image...'
                script {
                    dockerImage = docker.build("${DOCKER_IMAGE}:${DOCKER_TAG}", "-f ${DOCKERFILE_DIR}/Dockerfile .")
                }
            }
        }

        stage('Push to Nexus') {
            steps {
                echo 'Pushing Docker image to Nexus...'
                script {
                    docker.withRegistry("${NEXUS_URL}", "${NEXUS_CREDENTIALS_ID}") {
                        dockerImage.push()
                    }
                }
            }
        }

        stage('Deploy') {
            steps {
                echo 'Deploying...'
                sshagent (credentials: ['APP-JENKINS-SSH']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} '
                        cd ${BACKEND_DIR}
                        git pull ${GIT_REPO} main
                        /root/restart-backend.sh
                    '
                    """
                }
            }
        }
         stage('SonarQube Analysis') {
            steps {
                echo 'SonarQube Analysis...'
                sshagent (credentials: ['APP-JENKINS-SSH']) {
                    sh """
                    ssh -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_IP} '
                        cd ${BACKEND_DIR}
                        /opt/sonar-scanner/bin/sonar-scanner
                    '
                    """
                }
            }
        }
    }

    post {
        success {
            echo 'Pipeline succeeded!'
        }
        failure {
            echo 'Pipeline failed!'
        }
    }
}
