pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                git url: 'git@github.com:MahrezBH/mcm-backend.git', branch: 'main'
            }
        }

        stage('Build') {
            steps {
                echo 'Building..'
                // Add your build steps here
            }
        }

        stage('Test') {
            steps {
                echo 'Testing..'
                // Add your test steps here
            }
        }

        stage('Deploy') {
            steps {
                echo 'Deploying....'
                // Add your deploy steps here
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
