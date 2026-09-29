param name string
param location string
param tags object
param workspaceId string
param allowedIps array

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: { name: 'basic' }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    disableLocalAuth: true // solo Entra ID / RBAC
    publicNetworkAccess: 'enabled'
    networkRuleSet: {
      ipRules: [for ip in allowedIps: { value: ip }]
    }
  }
}

resource diag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'to-law'
  scope: search
  properties: {
    workspaceId: workspaceId
    logs: [{ categoryGroup: 'allLogs', enabled: true }]
  }
}

output name string = search.name
output endpoint string = 'https://${search.name}.search.windows.net'
