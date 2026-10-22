#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

mkdir -p .deployment
az bicep build --file iac/main.bicep --outfile .deployment/main.json
for environment in dev prod; do
  az bicep build-params --file "iac/environments/$environment.bicepparam" \
    --outfile ".deployment/$environment.parameters.json"
done
python3 -m unittest discover -s tests/infrastructure -v
dotnet test tests/NovaBank.Api.Tests/NovaBank.Api.Tests.csproj --configuration Release --verbosity minimal
