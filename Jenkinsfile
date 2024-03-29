pipeline {
    agent {
        docker {
            reuseNode false
            image 'caufieldjh/ubuntu20-python-3-9-14-dev:2'
        }
    }
    triggers{
        cron('0 0 * * 6')
    }
    environment {
        BUILDSTARTDATE = sh(script: "echo `date +%Y%m%d`", returnStdout: true).trim()
        S3PROJECTDIR = 'kg-obo' // no trailing slash

        // Distribution ID for the AWS CloudFront for this bucket
        // used solely for invalidations
        AWS_CLOUDFRONT_DISTRIBUTION_ID = 'EUVSWXZQBXCFP'

        // Some imports use an outdated scikit-learn alias.
        // This makes that usage OK for pip.
        SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL='True'

    }
    options {
        timestamps()
    }
    stages {
        // Very first: pause for a minute to give a chance to
        // cancel and clean the workspace before use.
        stage('Ready and clean') {
            steps {
                // Give us a minute to cancel if we want.
                sleep time: 30, unit: 'SECONDS'
            }
        }

        stage('Initialize') {
            steps {
                // print some info
                dir('./gitrepo') {
                    sh 'env > env.txt'
                    sh 'echo $BRANCH_NAME > branch.txt'
                    sh 'echo "$BRANCH_NAME"'
                    sh 'cat env.txt'
                    sh 'cat branch.txt'
                    sh "echo $BUILDSTARTDATE > dow.txt"
                    sh "echo $BUILDSTARTDATE"
                    sh "python3.9 --version"
                    sh "id"
                    sh "whoami" // this should be jenkinsuser
                    // if the above fails, then the docker host didn't start the docker
                    // container as a user that this image knows about. This will
                    // likely cause lots of problems (like trying to write to $HOME
                    // directory that doesn't exist, etc), so we should fail here and
                    // have the user fix this
                }
            }
        }

        stage('Build kg-obo') {
            steps {
                dir('./gitrepo') {
                    git(
                            url: 'https://github.com/Knowledge-Graph-Hub/kg-obo',
                            branch: env.BRANCH_NAME
                    )
                    sh '/usr/bin/python3.9 -m venv venv'
                    sh '. venv/bin/activate'
                    sh './venv/bin/pip install pathlib' // fix for build config issues with pathlib
                    sh './venv/bin/pip install .'
                }
            }
        }

        stage('Transform') {
            steps {
                dir('./gitrepo') {
                    withCredentials([
                            file(credentialsId: 's3cmd_kg_hub_push_configuration', variable: 'S3CMD_CFG'),
                            file(credentialsId: 'aws_kg_hub_push_json', variable: 'AWS_JSON'),
                            string(credentialsId: 'aws_kg_hub_access_key', variable: 'AWS_ACCESS_KEY_ID'),
                            string(credentialsId: 'aws_kg_hub_secret_key', variable: 'AWS_SECRET_ACCESS_KEY')]) {
                            script {
                                if (env.BRANCH_NAME != 'main') {
                                    echo "Transforming with --s3_test since we aren't on main/master branch"
                                    sh '. venv/bin/activate && env && python3.9 run.py --s3_test --bucket fake_bucket --no_dl_progress'
                                } else {
                                    sh '. venv/bin/activate && env && python3.9 run.py --bucket kg-hub-public-data --no_dl_progress --force_index_refresh'
                                }
                            }
                            
                    }
                }
            }
        }
    }


    post {
        always {
            echo 'In always'
            echo 'Cleaning workspace...'
            cleanWs()
        }
        success {
            echo 'I succeeded!'
        }
        unstable {
            echo 'I am unstable :/'
        }
        failure {
            echo 'I failed :('
        }
        changed {
            echo 'Things were different before...'
        }
    }

}
