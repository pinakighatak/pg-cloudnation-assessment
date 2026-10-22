param name string
param storageName string
@allowed(['westeurope', 'northeurope'])
param location string
param zoneRedundant bool
param identityId string
param identityClientId string
param identityPrincipalId string
param identityName string
param subnetId string
param databaseHost string
param apiClientId string
param apiAudience string
param allowedCallerClientId string
param insightsConnectionString string
param workspaceId string
param tags object

module storage 'br/public:avm/res/storage/storage-account:0.33.1' = {
  name: 'host-storage'
  params: {
    name: storageName
    location: location
    skuName: zoneRedundant ? 'Standard_ZRS' : 'Standard_LRS'
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    allowBlobPublicAccess: false
    publicNetworkAccess: 'Enabled'
    minimumTlsVersion: 'TLS1_2'
    networkAcls: {
      bypass: 'None'
      defaultAction: 'Deny'
      virtualNetworkRules: [{ id: subnetId, action: 'Allow' }]
      ipRules: []
    }
    blobServices: {
      containers: [{ name: 'deployment', publicAccess: 'None' }]
      deleteRetentionPolicyEnabled: true
      deleteRetentionPolicyDays: 7
      containerDeleteRetentionPolicyEnabled: true
      containerDeleteRetentionPolicyDays: 7
      diagnosticSettings: [
        {
          name: 'central'
          workspaceResourceId: workspaceId
          logCategoriesAndGroups: [{ categoryGroup: 'allLogs' }]
        }
      ]
    }
    roleAssignments: [
      {
        principalId: identityPrincipalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'Storage Blob Data Owner'
      }
      {
        principalId: identityPrincipalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'Storage Queue Data Contributor'
      }
      {
        principalId: identityPrincipalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'Storage Account Contributor'
      }
    ]
    tags: tags
    enableTelemetry: false
  }
}

module plan 'br/public:avm/res/web/serverfarm:0.7.0' = {
  name: 'hosting-plan'
  params: {
    name: 'plan-${name}'
    location: location
    kind: 'functionapp'
    reserved: true
    skuName: 'FC1'
    skuCapacity: 0
    zoneRedundant: zoneRedundant
    tags: tags
    enableTelemetry: false
  }
}

module site 'br/public:avm/res/web/site:0.24.0' = {
  name: 'api'
  params: {
    name: name
    location: location
    kind: 'functionapp,linux'
    serverFarmResourceId: plan.outputs.resourceId
    managedIdentities: { userAssignedResourceIds: [identityId] }
    virtualNetworkSubnetResourceId: subnetId
    httpsOnly: true
    publicNetworkAccess: 'Enabled'
    clientAffinityEnabled: false
    basicPublishingCredentialsPolicies: [
      { name: 'ftp', allow: false }
      { name: 'scm', allow: false }
    ]
    siteConfig: {
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      ftpsState: 'Disabled'
    }
    functionAppConfig: {
      runtime: { name: 'dotnet-isolated', version: '10.0' }
      deployment: {
        storage: {
          type: 'blobContainer'
          value: 'https://${storage.outputs.name}.blob.${environment().suffixes.storage}/deployment'
          authentication: {
            type: 'UserAssignedIdentity'
            userAssignedIdentityResourceId: identityId
          }
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: 40
        instanceMemoryMB: 512
        triggers: { http: { perInstanceConcurrency: 4 } }
        alwaysReady: zoneRedundant ? [{ name: 'http', instanceCount: 2 }] : []
      }
    }
    configs: [
      {
        name: 'appsettings'
        properties: {
          AzureWebJobsStorage__accountName: storage.outputs.name
          AzureWebJobsStorage__credential: 'managedidentity'
          AzureWebJobsStorage__clientId: identityClientId
          APPLICATIONINSIGHTS_CONNECTION_STRING: insightsConnectionString
          APPLICATIONINSIGHTS_AUTHENTICATION_STRING: 'ClientId=${identityClientId};Authorization=AAD'
          AZURE_CLIENT_ID: identityClientId
          Database__Host: databaseHost
          Database__Name: 'novabank'
          Database__Username: identityName
        }
      }
      {
        name: 'authsettingsV2'
        properties: {
          platform: { enabled: true }
          globalValidation: {
            requireAuthentication: true
            unauthenticatedClientAction: 'Return401'
          }
          identityProviders: {
            azureActiveDirectory: {
              enabled: true
              registration: {
                clientId: apiClientId
                openIdIssuer: '${environment().authentication.loginEndpoint}${tenant().tenantId}/v2.0'
              }
              validation: {
                allowedAudiences: [apiAudience, apiClientId]
                defaultAuthorizationPolicy: {
                  allowedApplications: [allowedCallerClientId]
                }
              }
            }
          }
          httpSettings: { requireHttps: true }
        }
      }
    ]
    diagnosticSettings: [
      {
        name: 'central'
        workspaceResourceId: workspaceId
        logCategoriesAndGroups: [{ categoryGroup: 'allLogs' }]
        metricCategories: [{ category: 'AllMetrics' }]
      }
    ]
    tags: tags
    enableTelemetry: false
  }
}

output name string = site.outputs.name
output hostname string = site.outputs.defaultHostname
output storageName string = storage.outputs.name
