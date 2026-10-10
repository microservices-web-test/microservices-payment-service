pipeline {
  agent any
  options {
    timestamps()
    disableConcurrentBuilds()
    timeout(time: 30, unit: 'MINUTES')
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }
  triggers {
    // Auto-build when GitHub sends a push webhook to Jenkins.
    //   Payload URL : http://141.147.71.111:8080/github-webhook/
    //   Content type: application/json
    //   Events      : Just the push event
    githubPush()
    // Fallback (Jenkins polls every 5 min):
    // pollSCM('H/5 * * * *')
  }
  environment {
    OCIR_REGISTRY  = 'lhr.ocir.io'
    OCI_TENANCY_NS = 'lryjhgnewmyj'
    IMAGE_REPO     = 'microservices-payment'
    IMAGE_NAME     = "${OCIR_REGISTRY}/${OCI_TENANCY_NS}/${IMAGE_REPO}"
    // ---- k3s target ----
    K8S_NAMESPACE  = 'microservices'
    K8S_DEPLOYMENT = 'payment-service'
    K8S_CONTAINER  = 'payment-service'
    PULL_SECRET    = 'ocir-secret'
  }
  stages {
    stage('Checkout') {
      steps {
        checkout scm
        script {
          env.GIT_SHA   = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
          env.IMAGE_TAG = "${env.BUILD_NUMBER}-${env.GIT_SHA}"
          echo "Building ${IMAGE_NAME}:${env.IMAGE_TAG}"
        }
      }
    }
    stage('Build image (arm64)') {
      steps {
        sh '''
          set -eu
          docker build --pull \
            -t "${IMAGE_NAME}:${IMAGE_TAG}" \
            -t "${IMAGE_NAME}:latest" \
            .
        '''
      }
    }
    stage('Scan image (Trivy, optional)') {
      steps {
        sh '''
          set -eu
          if command -v trivy >/dev/null 2>&1; then
            trivy image --severity HIGH,CRITICAL --ignore-unfixed "${IMAGE_NAME}:${IMAGE_TAG}" || true
          else
            echo "trivy not installed on agent; skipping image scan"
          fi
        '''
      }
    }
    stage('Push to OCIR') {
      steps {
        withCredentials([usernamePassword(
          credentialsId: 'ocir-credentials',
          usernameVariable: 'OCIR_USER',
          passwordVariable: 'OCIR_TOKEN')]) {
          sh '''
            set -eu
            echo "${OCIR_TOKEN}" | docker login "${OCIR_REGISTRY}" -u "${OCIR_USER}" --password-stdin
            docker push "${IMAGE_NAME}:${IMAGE_TAG}"
            docker push "${IMAGE_NAME}:latest"
            docker logout "${OCIR_REGISTRY}" || true
          '''
        }
      }
    }
    // ---------------------------------------------------------------------
    // The in-cluster work is split into three visible stages so the Jenkins
    // stage view tells a clear story: bring the DB up -> migrate it -> deploy
    // the app. Each stage needs the kubeconfig (Postgres, Flyway and the app
    // all live inside k3s).
    // ---------------------------------------------------------------------
    stage('Provision Postgres (k3s)') {
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
          sh '''
            set -eu
            export KUBECONFIG="${KUBECONFIG_FILE}"
            # Namespace (shared; harmless if it already exists).
            kubectl apply -f k8s/namespace.yaml
            # DB credentials + the dedicated Postgres (PVC / Deployment / Service).
            kubectl apply -f k8s/secret.yaml
            kubectl apply -f k8s/postgres.yaml
            # Block until the database is actually accepting connections.
            echo ">> waiting for payment-db to become Ready..."
            kubectl -n "${K8S_NAMESPACE}" rollout status deployment/payment-db --timeout=180s
          '''
        }
      }
    }
    stage('DB migration (Flyway)') {
      steps {
        withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE')]) {
          sh '''
            set -eu
            export KUBECONFIG="${KUBECONFIG_FILE}"

            # Ship the repo's SQL to the cluster as a ConfigMap (the Flyway Job
            # mounts it at /flyway/sql).
            kubectl -n "${K8S_NAMESPACE}" create configmap payment-migrations \
              --from-file=db/migrations/ \
              --dry-run=client -o yaml | kubectl apply -f -

            # A Job's pod template is immutable, so delete any previous run first,
            # then (re)create it. Flyway is idempotent -> safe to run every build.
            kubectl -n "${K8S_NAMESPACE}" delete job payment-migrate --ignore-not-found
            kubectl apply -f k8s/migration-job.yaml

            # Stream the Flyway container's output straight into this console so
            # you can watch it: connect -> check schema history -> apply pending
            # migrations -> exit. First wait for the Job's pod to appear.
            echo ">> waiting for the payment-migrate pod to start..."
            POD=""
            for i in $(seq 1 60); do
              POD=$(kubectl -n "${K8S_NAMESPACE}" get pods -l job-name=payment-migrate \
                      -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
              [ -n "$POD" ] && break
              sleep 2
            done
            echo ">> streaming Flyway logs from pod: ${POD}"
            kubectl -n "${K8S_NAMESPACE}" logs -f "job/payment-migrate" || true

            # Assert the Job actually succeeded; dump diagnostics and fail if not.
            if ! kubectl -n "${K8S_NAMESPACE}" wait --for=condition=complete \
                 job/payment-migrate --timeout=180s; then
              echo "!! Flyway migration did NOT complete successfully:"
              kubectl -n "${K8S_NAMESPACE}" logs "job/payment-migrate" --tail=-1 || true
              kubectl -n "${K8S_NAMESPACE}" describe job payment-migrate || true
              exit 1
            fi
            echo ">> migrations applied successfully."
          '''
        }
      }
    }
    stage('Deploy app (k3s)') {
      steps {
        withCredentials([
          file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG_FILE'),
          usernamePassword(credentialsId: 'ocir-credentials',
                           usernameVariable: 'OCIR_USER',
                           passwordVariable: 'OCIR_TOKEN')]) {
          sh '''
            set -eu
            export KUBECONFIG="${KUBECONFIG_FILE}"
            # Private-registry pull secret (idempotent create-or-update) — the
            # app image is private, so the cluster needs credentials to pull it.
            kubectl -n "${K8S_NAMESPACE}" create secret docker-registry "${PULL_SECRET}" \
              --docker-server="${OCIR_REGISTRY}" \
              --docker-username="${OCIR_USER}" \
              --docker-password="${OCIR_TOKEN}" \
              --dry-run=client -o yaml | kubectl apply -f -
            # Internal Service (ClusterIP payment-service:5000).
            kubectl apply -f k8s/service.yaml
            # App Deployment with the freshly built, immutable tag.
            sed "s#${IMAGE_NAME}:v1#${IMAGE_NAME}:${IMAGE_TAG}#g" k8s/deployment.yaml \
              | kubectl apply -f -
            kubectl -n "${K8S_NAMESPACE}" set image \
              "deployment/${K8S_DEPLOYMENT}" \
              "${K8S_CONTAINER}=${IMAGE_NAME}:${IMAGE_TAG}"
            # Wait for rollout; auto-rollback on failure.
            if ! kubectl -n "${K8S_NAMESPACE}" rollout status \
                 "deployment/${K8S_DEPLOYMENT}" --timeout=180s; then
              echo "Rollout failed; rolling back."
              kubectl -n "${K8S_NAMESPACE}" rollout undo "deployment/${K8S_DEPLOYMENT}"
              exit 1
            fi
          '''
        }
      }
    }
  }
  post {
    success {
      echo "Deployed ${IMAGE_NAME}:${IMAGE_TAG} to k3s namespace ${K8S_NAMESPACE} (ClusterIP payment-service:5000)."
    }
    always {
      sh 'docker image rm "${IMAGE_NAME}:${IMAGE_TAG}" "${IMAGE_NAME}:latest" >/dev/null 2>&1 || true'
    }
  }
}
