pipeline {
    agent any

    environment {
        SERVER_IP = '65.21.108.31'
        SERVER_USER = 'root'
        GIT_REPO = 'git@github.com:MahrezBH/mcm-backend.git'
        BACKEND_DIR = '/root/mcm-backend'
        NEXUS_URL = 'http://37.27.4.176:8081'
        NEXUS_REPO = 'ilef'
        NEXUS_CREDENTIALS_ID = 'nexus-credentials'
        DOCKER_IMAGE = 'mcm-backend'
        VERSION_FILE = 'version.txt'
        DOCKERFILE_DIR = 'ilef_cloud'
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out code...'
                git url: "${GIT_REPO}", branch: 'main'
            }
        }

        stage('Read Version') {
            steps {
                script {
                    def version = readFile("${VERSION_FILE}").trim()
                    def newVersion = version.toInteger() + 1
                    env.DOCKER_TAG = newVersion.toString()
                    writeFile file: "${VERSION_FILE}", text: env.DOCKER_TAG
                    echo "New Docker tag: ${env.DOCKER_TAG}"
                }
            }
        }

        stage('Commit New Version') {
            steps {
                script {
                    echo "Configuring Git..."
                    sh 'git config user.email "mahrez.benhamad@gmail.com"'
                    sh 'git config user.name "MahrezBH"'
                    sh 'git add ${VERSION_FILE}'
                    sh 'git commit -m "Increment version to ${DOCKER_TAG}" || echo "No changes to commit"'
                    sh 'git push origin main || echo "Nothing to push"'
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
