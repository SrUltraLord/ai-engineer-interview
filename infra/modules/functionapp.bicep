param name string
param location string
param tags object
param storageName string
param docsStorageName string
param appInsightsConnectionString string
param openAiEndpoint string
param embeddingDeployment string
param searchEndpoint string

// Storage propio del host de la Function (Consumption Linux requiere file share => shared key).
resource hostStorage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

var hostConn = 'DefaultEndpointsProtocol=https;AccountName=${hostStorage.name};AccountKey=${hostStorage.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: 'plan-${name}'
  location: location
  tags: tags
  kind: 'linux'
  sku: { name: 'Y1', tier: 'Dynamic' }
  properties: { reserved: true }
}

resource func 'Microsoft.Web/sites@2023-12-01' = {
  name: name
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      appSettings: [
        { name: 'AzureWebJobsStorage', value: hostConn }
        { name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING', value: hostConn }
        { name: 'WEBSITE_CONTENTSHARE', value: toLower(name) }
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
        // Conexión por identidad para el blob trigger (binding connection = "DocsStorage")
        { name: 'DocsStorage__blobServiceUri', value: 'https://${docsStorageName}.blob.${environment().suffixes.storage}' }
        { name: 'AZURE_OPENAI_ENDPOINT', value: openAiEndpoint }
        { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: embeddingDeployment }
        { name: 'AZURE_SEARCH_ENDPOINT', value: searchEndpoint }
      ]
    }
  }
}

output principalId string = func.identity.principalId
output name string = func.name
