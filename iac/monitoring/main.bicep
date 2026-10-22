param name string
@allowed(['westeurope', 'northeurope'])
param location string
param logReaderGroupIds string[]
param identityPrincipalId string
param tags object

module workspace 'br/public:avm/res/operational-insights/workspace:0.16.1' = {
  name: 'workspace'
  params: {
    name: 'log-${name}'
    location: location
    dataRetention: 400
    forceCmkForQuery: false
    features: {
      disableLocalAuth: true
      enableLogAccessUsingOnlyResourcePermissions: false
    }
    roleAssignments: [for groupId in logReaderGroupIds: {
      principalId: groupId
      principalType: 'Group'
      roleDefinitionIdOrName: 'Log Analytics Reader'
    }]
    tags: tags
    enableTelemetry: false
  }
}

module insights 'br/public:avm/res/insights/component:0.8.0' = {
  name: 'application-insights'
  params: {
    name: 'appi-${name}'
    location: location
    workspaceResourceId: workspace.outputs.resourceId
    disableLocalAuth: true
    disableIpMasking: false
    retentionInDays: 365
    roleAssignments: [
      {
        principalId: identityPrincipalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: 'Monitoring Metrics Publisher'
      }
    ]
    tags: tags
    enableTelemetry: false
  }
}

output workspaceId string = workspace.outputs.resourceId
output insightsId string = insights.outputs.resourceId
output insightsConnectionString string = insights.outputs.connectionString
