pipeline {
    agent any

    environment {
        SERVER_IP = '37.27.185.86'
        SERVER_USER = 'root'
        GIT_REPO = 'git@github.com:MahrezBH/mcm-backend.git'
        BACKEND_DIR = '/root/mcm-backend'
        NEXUS_URL = 'http://37.27.10.145:8081'
        NEXUS_REPO = 'ilef'
        NEXUS_CREDENTIALS_ID = 'nexus-credentials'
        DOCKER_IMAGE = 'mcm-backend'
        DOCKER_TAG = 'latest'
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out code...'
                sshagent (credentials: ['MahrezBH-GITHUB']) {
                    sh 'git clone ${GIT_REPO} ${BACKEND_DIR}'
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                echo 'Building Docker image...'
                script {
                    dockerImage = docker.build("${DOCKER_IMAGE}:${DOCKER_TAG}")
                }
            }
        }

        stage('Push to Nexus') {
            steps {
                echo 'Pushing Docker image to Nexus...'
                script {
                    withDockerRegistry([ credentialsId: "${NEXUS_CREDENTIALS_ID}", url: "${NEXUS_URL}" ]) {
                        dockerImage.push()
                    }
                }
            }
        }

        stage('Deploy') {
            steps {
                echo 'Deploying...'
                sshagent (credentials: ['MahrezBH-JENKINS-SSH']) {
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
