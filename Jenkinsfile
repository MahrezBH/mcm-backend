pipeline {
    agent any

    environment {
        SERVER_IP = '37.27.185.86'
        SERVER_USER = 'root'
        GIT_REPO = 'git@github.com:MahrezBH/mcm-backend.git'
        BACKEND_DIR = '/root/mcm-backend'
    }

    stages {
        stage('Checkout') {
            steps {
                git url: "${GIT_REPO}", branch: 'main'
            }
        }

        stage('Build') {
            steps {
                echo 'Building...'
                // Add your build steps here
            }
        }

        stage('Test') {
            steps {
                echo 'Testing...'
                // Add your test steps here
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
