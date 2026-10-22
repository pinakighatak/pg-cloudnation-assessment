param name string
@allowed(['westeurope', 'northeurope'])
param location string
@allowed(['dev', 'prod'])
param environmentName string
param sourceServerResourceId string = ''
param databaseAdminObjectId string
param databaseAdminName string
param endpointSubnetId string
param privateDnsZoneId string
param workspaceId string
param alertActionGroupId string
param tags object

var isReplica = !empty(sourceServerResourceId)
var isProduction = environmentName == 'prod'

module server 'br/public:avm/res/db-for-postgre-sql/flexible-server:0.13.2' = {
  name: 'server'
  params: {
    name: name
    location: location
    tenantId: tenant().tenantId
    administrators: [
      {
        objectId: databaseAdminObjectId
        principalName: databaseAdminName
        principalType: 'ServicePrincipal'
        tenantId: tenant().tenantId
      }
    ]
    skuName: isProduction ? 'Standard_D2ds_v5' : 'Standard_B1ms'
    tier: isProduction ? 'GeneralPurpose' : 'Burstable'
    version: '17'
    availabilityZone: -1
    highAvailability: isProduction && !isReplica ? 'ZoneRedundant' : 'Disabled'
    backupRetentionDays: isProduction ? 35 : 7
    geoRedundantBackup: 'Disabled'
    storageSizeGB: 32
    autoGrow: 'Enabled'
    serverThreatProtection: isProduction ? 'Enabled' : 'Disabled'
    enableAdvancedThreatProtection: isProduction
    createMode: isReplica ? 'Replica' : 'Default'
    sourceServerResourceId: sourceServerResourceId
    publicNetworkAccess: 'Enabled'
    databases: isReplica ? [] : [
      {
        name: 'novabank'
        charset: 'UTF8'
        collation: 'en_US.utf8'
      }
    ]
    configurations: [
      {
        name: 'require_secure_transport'
        value: 'on'
        source: 'user-override'
      }
    ]
    privateEndpoints: [
      {
        name: 'pe-${name}'
        subnetResourceId: endpointSubnetId
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            { privateDnsZoneResourceId: privateDnsZoneId }
          ]
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

// An explicit seconds-based criterion is not exposed by the server AVM.
resource lagAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = if (isReplica) {
  name: '${name}-replica-lag'
  location: 'global'
  tags: tags
  properties: {
    description: 'Replica lag exceeds 15 minutes; investigate before the one-hour RPO is at risk.'
    severity: 1
    enabled: true
    scopes: [server.outputs.resourceId]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'replica-lag-seconds'
          criterionType: 'StaticThresholdCriterion'
          metricNamespace: 'Microsoft.DBforPostgreSQL/flexibleServers'
          metricName: 'physical_replication_delay_in_seconds'
          operator: 'GreaterThan'
          threshold: 900
          timeAggregation: 'Maximum'
        }
      ]
    }
    actions: [{ actionGroupId: alertActionGroupId }]
    autoMitigate: true
  }
}

output name string = server.outputs.name
output resourceId string = server.outputs.resourceId
output fqdn string = '${server.outputs.name}.postgres.database.azure.com'
