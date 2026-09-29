param name string
param location string
param tags object
param publisherEmail string
param publisherName string
param backendUrl string // https://<fqdn-agente>
param tenantId string
param apiAudience string

resource apim 'Microsoft.ApiManagement/service@2023-09-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: { name: 'Consumption', capacity: 0 }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
  }
}

resource api 'Microsoft.ApiManagement/service/apis@2023-09-01-preview' = {
  parent: apim
  name: 'docs-api'
  properties: {
    displayName: 'Docs RAG API'
    path: 'api/v1/docs'
    protocols: ['https']
    serviceUrl: '${backendUrl}/api/v1/docs'
    subscriptionRequired: false // la autenticación es el JWT de Entra ID
  }
}

resource query 'Microsoft.ApiManagement/service/apis/operations@2023-09-01-preview' = {
  parent: api
  name: 'query'
  properties: {
    displayName: 'Query documents'
    method: 'POST'
    urlTemplate: '/query'
  }
}

var policyXml = '''
<policies>
  <inbound>
    <base />
    <validate-jwt header-name="Authorization" failed-validation-httpcode="401" failed-validation-error-message="Unauthorized">
      <openid-config url="https://login.microsoftonline.com/TENANT_ID/v2.0/.well-known/openid-configuration" />
      <audiences><audience>API_AUDIENCE</audience></audiences>
    </validate-jwt>
    <rate-limit-by-key calls="60" renewal-period="60" counter-key="@(context.Request.IpAddress)" />
  </inbound>
  <backend><base /></backend>
  <outbound><base /></outbound>
  <on-error><base /></on-error>
</policies>'''

resource policy 'Microsoft.ApiManagement/service/apis/policies@2023-09-01-preview' = {
  parent: api
  name: 'policy'
  properties: {
    format: 'xml'
    value: replace(replace(policyXml, 'TENANT_ID', tenantId), 'API_AUDIENCE', apiAudience)
  }
}

output gatewayUrl string = apim.properties.gatewayUrl
