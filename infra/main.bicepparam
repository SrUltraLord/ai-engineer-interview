using 'main.bicep'

param baseName = 'docsrag'
param location = 'eastus2'

// Tras hacer push de las imágenes a ACR, sustituir por p.ej. '<acr>.azurecr.io/agent:v1' y puerto 8000
param agentImage = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param agentPort = 80
param mcpImage = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param mcpPort = 80

param allowedIps = []

param deployApim = true
param apimPublisherEmail = 'davidrey8822@gmail.com'
param apimPublisherName = 'Banco'
param apiAudience = 'api://REEMPLAZAR-client-id'
