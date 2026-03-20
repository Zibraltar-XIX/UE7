@echo off

set /p VERSION=Entrez la version de l'image :

if "%VERSION%"=="" (
    echo Version obligatoire.
    pause
    exit /b
)

set IMAGE=parzivalxix/alternance-tah-les-fous

docker buildx use multiarch-builder
docker buildx build --platform linux/amd64,linux/arm64 -f .\app\Dockerfile -t %IMAGE%:%VERSION% -t %IMAGE%:latest --push .

pause