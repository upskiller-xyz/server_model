export DAYLIGHT_SERVER_VERSION=$(cat src/__version__.py | cut -d '=' -f2 | xargs)
source .env
# scw registry namespace create name=${SCW_REGISTRY_NAMESPACE} project-id=${SCW_PROJECT_ID}
docker build -t rg.fr-par.scw.cloud/${SCW_SERVER}/${SCW_IMAGE}:${DAYLIGHT_SERVER_VERSION} .
docker push rg.fr-par.scw.cloud/${SCW_SERVER}/${SCW_IMAGE}:${DAYLIGHT_SERVER_VERSION}