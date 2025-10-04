pipeline {
    agent {
        kubernetes {
            yaml '''
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: kaniko
    image: gcr.io/kaniko-project/executor:v1.9.1-debug
    command:
    - /busybox/cat
    tty: true
    volumeMounts:
    - name: docker-config
      mountPath: /kaniko/.docker
  volumes:
  - name: docker-config
    emptyDir: {}
'''
        }
    }

    options {
        timeout(time: 30, unit: 'MINUTES')
    }

    environment {
        DOCKER_REGISTRY = 'container-registry-k8s-cmc.khacthienit.click/sideproject1'
        DOCKER_IMAGE = "${DOCKER_REGISTRY}/sideproject1-backend"
        COMMIT_ID = "${GIT_COMMIT.take(7)}"
        DEPLOY_ENV = 'production'
        REGISTRY_CREDENTIALS = credentials('ci-registry-cred')
    }

    stages {
        stage('Set Environment') {
            steps {
                script {
                    echo "Branch name: ${env.BRANCH_NAME}"
                    echo "Trimmed branch name: ${env.BRANCH_NAME.trim()}"
                    def branch = env.BRANCH_NAME.trim()

                    if (branch.startsWith('dev')) {
                        env.DEPLOY_ENV = 'development'
                    } else if (branch.startsWith('test')) {
                        env.DEPLOY_ENV = 'development'
                    } else if (branch.startsWith('prod')) {
                        env.DEPLOY_ENV = 'production'
                    } else {
                        error "Build in branch match with regex"
                    }
                }
            }
        }

        stage('Build và Push Docker Image') {
            when {
                anyOf {
                    expression { env.DEPLOY_ENV == 'development' }
                    expression { env.DEPLOY_ENV == 'production' }
                }
            }
            steps {
                container('kaniko') {
                    sh """
                    echo "Tạo docker config.json cho Kaniko"
                    mkdir -p /kaniko/.docker
                    echo "{\\"auths\\":{\\"${DOCKER_REGISTRY}\\":{\\"username\\":\\"$REGISTRY_CREDENTIALS_USR\\",\\"password\\":\\"$REGISTRY_CREDENTIALS_PSW\\"}}}" > /kaniko/.docker/config.json
                    cat /kaniko/.docker/config.json

                    echo "Current directory: \$(pwd)"
                    ls -la

                    echo "Building and pushing Docker image to ${DOCKER_IMAGE}:${COMMIT_ID}-${DEPLOY_ENV}"
                    /kaniko/executor --context . \
                        --destination ${DOCKER_IMAGE}:${COMMIT_ID}-${DEPLOY_ENV} \
                        --verbosity debug
                    """
                }
            }
        }
    }
}
