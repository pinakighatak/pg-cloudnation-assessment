targetScope = 'subscription'

@allowed(['dev', 'prod'])
param environmentName string

@allowed(['westeurope'])
param primaryLocation string = 'westeurope'

@allowed(['northeurope'])
param recoveryLocation string = 'northeurope'

@minLength(1)
@maxLength(12)
param workloadName string = 'novabank'

param databaseAdminObjectId string
param databaseAdminName string
param apiClientId string
param apiAudience string
param allowedCallerClientId string

@minLength(1)
param logReaderGroupIds string[]

@description('Existing Monitor action group receiving production replica-lag alerts.')
param alertActionGroupId string

var tags = {
  workload: workloadName
  environment: environmentName
  managedBy: 'bicep'
  classification: 'synthetic-demo'
}

resource primaryGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${workloadName}-${environmentName}-primary'
  location: primaryLocation
  tags: tags
}

resource recoveryGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = if (environmentName == 'prod') {
  name: 'rg-${workloadName}-${environmentName}-recovery'
  location: recoveryLocation
  tags: tags
}

module primary 'regional.bicep' = {
  name: '${environmentName}-primary'
  scope: primaryGroup
  params: {
    environmentName: environmentName
    location: primaryLocation
    isRecovery: false
    workloadName: workloadName
    databaseAdminObjectId: databaseAdminObjectId
    databaseAdminName: databaseAdminName
    apiClientId: apiClientId
    apiAudience: apiAudience
    allowedCallerClientId: allowedCallerClientId
    logReaderGroupIds: logReaderGroupIds
    alertActionGroupId: alertActionGroupId
    tags: tags
  }
}

module recovery 'regional.bicep' = if (environmentName == 'prod') {
  name: '${environmentName}-recovery'
  scope: recoveryGroup!
  params: {
    environmentName: environmentName
    location: recoveryLocation
    isRecovery: true
    workloadName: workloadName
    sourceServerResourceId: primary.outputs.resources.serverId
    databaseAdminObjectId: databaseAdminObjectId
    databaseAdminName: databaseAdminName
    apiClientId: apiClientId
    apiAudience: apiAudience
    allowedCallerClientId: allowedCallerClientId
    logReaderGroupIds: logReaderGroupIds
    alertActionGroupId: alertActionGroupId
    tags: tags
  }
}

// Diagnostic settings are extension resources, not standalone AVM workloads.
resource activityLogs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: '${workloadName}-${environmentName}-activity'
  properties: {
    workspaceId: primary.outputs.resources.workspaceId
    logs: [{ categoryGroup: 'allLogs', enabled: true }]
  }
}

resource recoveryActivityLogs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (environmentName == 'prod') {
  name: '${workloadName}-${environmentName}-recovery-activity'
  properties: {
    workspaceId: recovery!.outputs.resources.workspaceId
    logs: [{ categoryGroup: 'allLogs', enabled: true }]
  }
}

output regions array = concat([primary.outputs.resources], environmentName == 'prod' ? [recovery!.outputs.resources] : [])
