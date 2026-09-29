param name string
param location string
param tags object
param environmentId string
param image string
param targetPort int
param external bool
param identityId string
param acrServer string
param env array = []
param minReplicas int = 1
param maxReplicas int = 3

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identityId}': {} }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: external
        targetPort: targetPort
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        { server: acrServer, identity: identityId }
      ]
    }
    template: {
      containers: [
        {
          name: name
          image: image
          env: env
          resources: { cpu: json('0.5'), memory: '1Gi' }
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          { name: 'http', http: { metadata: { concurrentRequests: '50' } } }
        ]
      }
    }
  }
}

output fqdn string = app.properties.configuration.ingress.fqdn
