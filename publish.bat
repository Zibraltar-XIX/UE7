@echo off

set /p VERSION=Entrez la version de l'image :

if "%VERSION%"=="" (
    echo Version obligatoire.
    pause
    exit /b
)

set IMAGE=parzivalxix/alternance-tah-les-fous

docker buildx create --use --name multiarch-builder
docker buildx inspect --bootstrap

docker buildx build --platform linux/amd64,linux/arm64 -f .\app\Dockerfile -t %IMAGE%:%VERSION% -t %IMAGE%:latest --push .

pause