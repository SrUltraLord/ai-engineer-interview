targetScope = 'resourceGroup'

@description('Prefijo corto para nombrar recursos (minúsculas, 3-10 caracteres).')
@minLength(3)
@maxLength(10)
param baseName string = 'docsrag'

param location string = 'eastus2'

@description('true = despliega solo Azure OpenAI + modelos (y Log Analytics); el resto de recursos se omite.')
param modelsOnly bool = true

@description('Object ID del usuario/identidad que ejecuta la app localmente; recibe "Cognitive Services OpenAI User". Vacío = no asignar. Obtener con: az ad signed-in-user show --query id -o tsv')
param developerPrincipalId string = ''

@description('Imagen del agente (FastAPI + LangChain). Por defecto un placeholder.')
param agentImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param agentPort int = 80

@description('Imagen del servidor MCP. Por defecto un placeholder.')
param mcpImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param mcpPort int = 80

@description('IPs/CIDR permitidas en Storage, Key Vault, Search y OpenAI. Vacío = sin restricción de IP (solo auth Entra/RBAC).')
param allowedIps array = []

param deployApim bool = true
param apimPublisherEmail string = 'admin@example.com'
param apimPublisherName string = 'Banco'
@description('Tenant de Entra ID para validate-jwt.')
param tenantId string = subscription().tenantId
@description('Audience (App ID URI / client id) del API en Entra ID.')
param apiAudience string = ''

param chatModel object = { name: 'chat-main', model: 'gpt-4.1', version: '2025-04-14', capacity: 30 }
param fallbackModel object = { name: 'chat-fallback', model: 'gpt-4.1-mini', version: '2025-04-14', capacity: 30 }
param embeddingModel object = { name: 'embeddings', model: 'text-embedding-3-small', version: '1', capacity: 30 }

var tags = { workload: 'docs-rag', environment: 'mvp', managedBy: 'bicep' }
var suffix = take(uniqueString(resourceGroup().id), 6)
var full = !modelsOnly
var compact = toLower(replace(baseName, '-', ''))
var resName = '${compact}-${suffix}'

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: { name: resName, location: location, tags: tags }
}

module keyvault 'modules/keyvault.bicep' = if (full) {
  name: 'keyvault'
  params: {
    name: 'kv-${take(compact, 10)}-${suffix}'
    location: location
    tags: tags
    workspaceId: monitoring.outputs.workspaceId
    allowedIps: allowedIps
  }
}

module acr 'modules/acr.bicep' = if (full) {
  name: 'acr'
  params: { name: 'acr${compact}${suffix}', location: location, tags: tags }
}

module docsStorage 'modules/storage.bicep' = if (full) {
  name: 'docs-storage'
  params: { name: 'st${take(compact, 10)}${suffix}', location: location, tags: tags, allowedIps: allowedIps }
}

module search 'modules/search.bicep' = if (full) {
  name: 'search'
  params: {
    name: 'srch-${resName}'
    location: location
    tags: tags
    workspaceId: monitoring.outputs.workspaceId
    allowedIps: allowedIps
  }
}

module openai 'modules/openai.bicep' = {
  name: 'openai'
  params: {
    name: 'oai-${resName}'
    location: location
    tags: tags
    workspaceId: monitoring.outputs.workspaceId
    allowedIps: allowedIps
    developerPrincipalId: developerPrincipalId
    deployments: [chatModel, fallbackModel, embeddingModel]
  }
}

resource agentIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = if (full) {
  name: 'id-agent-${resName}'
  location: location
  tags: tags
}

resource mcpIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = if (full) {
  name: 'id-mcp-${resName}'
  location: location
  tags: tags
}

module function 'modules/functionapp.bicep' = if (full) {
  name: 'function'
  params: {
    name: 'func-${resName}'
    location: location
    tags: tags
    storageName: 'stfn${take(compact, 8)}${suffix}'
    docsStorageName: docsStorage!.outputs.name
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    openAiEndpoint: openai.outputs.endpoint
    embeddingDeployment: embeddingModel.name
    searchEndpoint: search!.outputs.endpoint
  }
}

module roles 'modules/roles.bicep' = if (full) {
  name: 'roles'
  params: {
    agentPrincipalId: agentIdentity!.properties.principalId
    mcpPrincipalId: mcpIdentity!.properties.principalId
    functionPrincipalId: function!.outputs.principalId
    acrName: acr!.outputs.name
    docsStorageName: docsStorage!.outputs.name
    searchName: search!.outputs.name
    openAiName: openai.outputs.name
  }
}

module caEnv 'modules/containerapps-env.bicep' = if (full) {
  name: 'ca-env'
  params: {
    name: 'cae-${resName}'
    location: location
    tags: tags
    workspaceName: monitoring.outputs.workspaceName
  }
}

module mcp 'modules/containerapp.bicep' = if (full) {
  name: 'app-mcp'
  dependsOn: [roles]
  params: {
    name: 'ca-mcp-${suffix}'
    location: location
    tags: tags
    environmentId: caEnv!.outputs.id
    image: mcpImage
    targetPort: mcpPort
    external: false // solo accesible dentro del environment
    identityId: mcpIdentity!.id
    acrServer: acr!.outputs.loginServer
    env: [
      { name: 'AZURE_CLIENT_ID', value: mcpIdentity!.properties.clientId }
      { name: 'AZURE_SEARCH_ENDPOINT', value: search!.outputs.endpoint }
      { name: 'AZURE_OPENAI_ENDPOINT', value: openai.outputs.endpoint }
      { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: embeddingModel.name }
      { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: monitoring.outputs.appInsightsConnectionString }
    ]
  }
}

module agent 'modules/containerapp.bicep' = if (full) {
  name: 'app-agent'
  dependsOn: [roles]
  params: {
    name: 'ca-agent-${suffix}'
    location: location
    tags: tags
    environmentId: caEnv!.outputs.id
    image: agentImage
    targetPort: agentPort
    external: true
    identityId: agentIdentity!.id
    acrServer: acr!.outputs.loginServer
    env: [
      { name: 'AZURE_CLIENT_ID', value: agentIdentity!.properties.clientId }
      { name: 'AZURE_OPENAI_ENDPOINT', value: openai.outputs.endpoint }
      { name: 'AZURE_OPENAI_DEPLOYMENT_PRIMARY', value: chatModel.name }
      { name: 'AZURE_OPENAI_DEPLOYMENT_FALLBACK', value: fallbackModel.name }
      { name: 'AZURE_SEARCH_ENDPOINT', value: search!.outputs.endpoint }
      { name: 'MCP_SERVER_URL', value: 'https://${mcp!.outputs.fqdn}/mcp' }
      { name: 'ENTRA_TENANT_ID', value: tenantId }
      { name: 'ENTRA_API_AUDIENCE', value: apiAudience }
      { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: monitoring.outputs.appInsightsConnectionString }
    ]
  }
}

module apim 'modules/apim.bicep' = if (full && deployApim) {
  name: 'apim'
  params: {
    name: 'apim-${resName}'
    location: location
    tags: tags
    publisherEmail: apimPublisherEmail
    publisherName: apimPublisherName
    backendUrl: 'https://${agent!.outputs.fqdn}'
    tenantId: tenantId
    apiAudience: apiAudience
  }
}

output agentUrl string = full ? 'https://${agent!.outputs.fqdn}' : ''
output mcpInternalUrl string = full ? 'https://${mcp!.outputs.fqdn}/mcp' : ''
output apimGatewayUrl string = full && deployApim ? apim!.outputs.gatewayUrl : ''
output acrLoginServer string = full ? acr!.outputs.loginServer : ''
output openAiEndpoint string = openai.outputs.endpoint
output openAiChatDeployment string = chatModel.name
output openAiFallbackDeployment string = fallbackModel.name
output openAiEmbeddingDeployment string = embeddingModel.name
output searchEndpoint string = full ? search!.outputs.endpoint : ''
output docsStorageName string = full ? docsStorage!.outputs.name : ''
output keyVaultName string = full ? keyvault!.outputs.name : ''
output functionAppName string = full ? function!.outputs.name : ''
