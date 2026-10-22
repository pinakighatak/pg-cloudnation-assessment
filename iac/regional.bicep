param environmentName string
@allowed(['westeurope', 'northeurope'])
param location string
param isRecovery bool
param workloadName string
param sourceServerResourceId string = ''
param databaseAdminObjectId string
param databaseAdminName string
param apiClientId string
param apiAudience string
param allowedCallerClientId string
param logReaderGroupIds string[]
param alertActionGroupId string
param tags object

var suffix = uniqueString(resourceGroup().id)
var name = '${workloadName}-${environmentName}-${isRecovery ? 'dr' : 'pri'}-${suffix}'

module identity 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = {
  name: 'api-identity'
  params: {
    name: 'id-${name}'
    location: location
    tags: tags
    enableTelemetry: false
  }
}

module monitoring 'monitoring/main.bicep' = {
  name: 'monitoring'
  params: {
    name: name
    location: location
    logReaderGroupIds: logReaderGroupIds
    identityPrincipalId: identity.outputs.principalId
    tags: tags
  }
}

module network 'networking/main.bicep' = {
  name: 'network'
  params: {
    name: name
    location: location
    addressPrefix: isRecovery ? '10.21.0.0/16' : '10.20.0.0/16'
    functionsPrefix: isRecovery ? '10.21.0.0/24' : '10.20.0.0/24'
    endpointsPrefix: isRecovery ? '10.21.1.0/24' : '10.20.1.0/24'
    tags: tags
  }
}

module database 'postgresql/main.bicep' = {
  name: 'postgresql'
  params: {
    name: 'psql-${name}'
    location: location
    environmentName: environmentName
    sourceServerResourceId: sourceServerResourceId
    databaseAdminObjectId: databaseAdminObjectId
    databaseAdminName: databaseAdminName
    endpointSubnetId: network.outputs.endpointSubnetId
    privateDnsZoneId: network.outputs.postgresDnsZoneId
    workspaceId: monitoring.outputs.workspaceId
    alertActionGroupId: alertActionGroupId
    tags: tags
  }
}

module functions 'functions/main.bicep' = {
  name: 'functions'
  params: {
    name: 'func-${name}'
    storageName: 'st${suffix}'
    location: location
    zoneRedundant: environmentName == 'prod' && !isRecovery
    identityId: identity.outputs.resourceId
    identityClientId: identity.outputs.clientId
    identityPrincipalId: identity.outputs.principalId
    identityName: identity.outputs.name
    subnetId: network.outputs.functionsSubnetId
    databaseHost: database.outputs.fqdn
    apiClientId: apiClientId
    apiAudience: apiAudience
    allowedCallerClientId: allowedCallerClientId
    insightsConnectionString: monitoring.outputs.insightsConnectionString
    workspaceId: monitoring.outputs.workspaceId
    tags: tags
  }
}

output resources object = {
  resourceGroup: resourceGroup().name
  location: location
  isRecovery: isRecovery
  serverId: database.outputs.resourceId
  serverName: database.outputs.name
  databaseHost: database.outputs.fqdn
  databaseName: 'novabank'
  identityName: identity.outputs.name
  identityPrincipalId: identity.outputs.principalId
  identityClientId: identity.outputs.clientId
  functionName: functions.outputs.name
  functionHost: functions.outputs.hostname
  storageName: functions.outputs.storageName
  workspaceId: monitoring.outputs.workspaceId
}
