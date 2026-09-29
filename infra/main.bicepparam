using 'main.bicep'

param baseName = 'docsrag'
param location = 'eastus2'

// true = solo Azure OpenAI + modelos (app local). false = infraestructura completa.
param modelsOnly = true
// Tu object ID (az ad signed-in-user show --query id -o tsv) para usar los modelos con `az login`
param developerPrincipalId = '2ee687d5-870e-4d98-9a88-091b235a7b55'

// Tras hacer push de las imágenes a ACR, sustituir por p.ej. '<acr>.azurecr.io/agent:v1' y puerto 8000
param agentImage = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param agentPort = 80
param mcpImage = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param mcpPort = 80

param allowedIps = []

param deployApim = true
param apimPublisherEmail = 'davidrey8822@gmail.com'
param apimPublisherName = 'Banco'
param apiAudience = 'api://8fdebb8e-ee88-4c4b-b6cd-aaf5d02f9dc6'
