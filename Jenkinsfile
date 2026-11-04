// Pipeline CI/CD: obtiene el código, prueba, construye la imagen y la ejecuta.
// Credenciales: crear en Jenkins una credencial "Username with password"
// con id "dnac-credentials" (no se escriben en este archivo).
pipeline {
    agent any

    environment {
        IMAGE = "devops-network-automation:${env.BUILD_NUMBER}"
    }

    stages {
        stage('Obtener codigo') {
            steps {
                checkout scm
            }
        }

        stage('Instalar dependencias') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --quiet -r requirements.txt
                '''
            }
        }

        stage('Pruebas') {
            steps {
                sh '''
                    . venv/bin/activate
                    python3 -m pytest -v --junitxml=reports/junit.xml
                '''
            }
            post {
                always {
                    junit 'reports/junit.xml'
                }
            }
        }

        stage('Analisis') {
            steps {
                sh '''
                    . venv/bin/activate
                    python3 -m py_compile app/*.py
                '''
            }
        }

        stage('Construir imagen') {
            steps {
                sh 'docker build -t $IMAGE .'
            }
        }

        stage('Desplegar') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dnac-credentials',
                                                  usernameVariable: 'DNAC_USERNAME',
                                                  passwordVariable: 'DNAC_PASSWORD')]) {
                    sh '''
                        mkdir -p reports
                        docker run --rm --user "$(id -u):$(id -g)" \
                            -e DNAC_URL=https://sandboxdnac.cisco.com \
                            -e DNAC_USERNAME -e DNAC_PASSWORD \
                            -e DNAC_VERIFY_SSL=false \
                            -v "$WORKSPACE/reports:/app/reports" \
                            $IMAGE --source api
                    '''
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/inventory.*', allowEmptyArchive: true
        }
    }
}
