param name string
param location string
param tags object
param workspaceId string
param allowedIps array
param deployments array // [{ name, model, version, capacity }]

resource account 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: name
    disableLocalAuth: true // solo Entra ID / RBAC
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: empty(allowedIps) ? 'Allow' : 'Deny'
      ipRules: [for ip in allowedIps: { value: ip }]
    }
  }
}

@batchSize(1)
resource dep 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = [for d in deployments: {
  parent: account
  name: d.name
  sku: { name: 'Standard', capacity: d.capacity }
  properties: {
    model: { format: 'OpenAI', name: d.model, version: d.version }
  }
}]

resource diag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'to-law'
  scope: account
  properties: {
    workspaceId: workspaceId
    logs: [{ categoryGroup: 'allLogs', enabled: true }]
  }
}

output name string = account.name
output endpoint string = account.properties.endpoint
