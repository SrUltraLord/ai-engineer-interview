# Infraestructura Azure (MVP backend)

Bicep para desplegar el backend RAG en `eastus2`: Container Apps (agente + MCP), Azure OpenAI, AI Search, Storage de documentos, Azure Function de embeddings, Key Vault, ACR, App Insights y APIM (opcional). No incluye frontend.

## Despliegue
```bash
az group create -n rg-docsrag -l eastus2
az deployment group what-if -g rg-docsrag -p main.bicepparam   # ejecutar desde infra/
az deployment group create  -g rg-docsrag -p main.bicepparam
```

## Pasos manuales
1. **Entra ID**: crear la App Registration del API y poner su audience en `apiAudience` (`main.bicepparam`).
2. **Imágenes**: `az acr build -r <acrLoginServer> -t agent:v1 ./agent` (y `mcp:v1`); actualizar `agentImage`/`mcpImage` y los puertos (p.ej. 8000) y redesplegar.
3. **Function**: publicar el código con `func azure functionapp publish <functionAppName>` (blob trigger sobre `documents`, conexión `DocsStorage`).
4. **Índice** de AI Search: crearlo con el rol de tu usuario (Search Service Contributor).

## Notas de seguridad
- OpenAI y Search con `disableLocalAuth`; el acceso es por identidad administrada + RBAC. El storage de documentos sin shared key.
- `allowedIps` vacío = sin filtro de IP. Si lo rellenas, añade también las IPs de salida de Container Apps/Function, o `Deny` las bloqueará. Para producción bancaria: VNet + private endpoints.
- El host de la Function (Y1 Linux) requiere shared key en su storage propio; la cadena queda en app settings (aceptable en MVP; migrar a Flex Consumption + identidad).
- El agente está expuesto directamente además de vía APIM; para restringirlo, limitar el ingress a las IPs de APIM.
- El MCP tiene ingress interno; el agente lo llama en `MCP_SERVER_URL`.
