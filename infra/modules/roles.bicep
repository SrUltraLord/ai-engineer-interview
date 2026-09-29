param agentPrincipalId string
param mcpPrincipalId string
param functionPrincipalId string
param acrName string
param docsStorageName string
param searchName string
param openAiName string

var roleIds = {
  acrPull: '7f951dda-4ed3-4680-a7ca-43fe172d538d'
  blobContributor: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
  searchIndexContributor: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
  searchIndexReader: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
  searchServiceContributor: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
  openAiUser: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = { name: acrName }
resource docs 'Microsoft.Storage/storageAccounts@2023-05-01' existing = { name: docsStorageName }
resource search 'Microsoft.Search/searchServices@2024-06-01-preview' existing = { name: searchName }
resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = { name: openAiName }

// ACR pull: agente y MCP
resource acrAgent 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, agentPrincipalId, roleIds.acrPull)
  properties: {
    principalId: agentPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.acrPull)
  }
}
resource acrMcp 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, mcpPrincipalId, roleIds.acrPull)
  properties: {
    principalId: mcpPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.acrPull)
  }
}

// Agente: Azure OpenAI + lectura del índice
resource agentOpenAi 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: openai
  name: guid(openai.id, agentPrincipalId, roleIds.openAiUser)
  properties: {
    principalId: agentPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.openAiUser)
  }
}
resource agentSearch 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, agentPrincipalId, roleIds.searchIndexReader)
  properties: {
    principalId: agentPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.searchIndexReader)
  }
}

// MCP: consulta el índice y genera embeddings de la consulta
resource mcpSearch 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, mcpPrincipalId, roleIds.searchIndexReader)
  properties: {
    principalId: mcpPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.searchIndexReader)
  }
}
resource mcpOpenAi 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: openai
  name: guid(openai.id, mcpPrincipalId, roleIds.openAiUser)
  properties: {
    principalId: mcpPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.openAiUser)
  }
}

// Function de indexación: lee blobs, genera embeddings y escribe en el índice
resource funcBlob 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: docs
  name: guid(docs.id, functionPrincipalId, roleIds.blobContributor)
  properties: {
    principalId: functionPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.blobContributor)
  }
}
resource funcOpenAi 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: openai
  name: guid(openai.id, functionPrincipalId, roleIds.openAiUser)
  properties: {
    principalId: functionPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.openAiUser)
  }
}
resource funcSearchData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, functionPrincipalId, roleIds.searchIndexContributor)
  properties: {
    principalId: functionPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.searchIndexContributor)
  }
}
resource funcSearchSvc 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: search
  name: guid(search.id, functionPrincipalId, roleIds.searchServiceContributor)
  properties: {
    principalId: functionPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIds.searchServiceContributor)
  }
}
