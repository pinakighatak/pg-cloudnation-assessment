param name string
@allowed(['westeurope', 'northeurope'])
param location string
param addressPrefix string
param functionsPrefix string
param endpointsPrefix string
param tags object

module vnet 'br/public:avm/res/network/virtual-network:0.10.2' = {
  name: 'vnet'
  params: {
    name: 'vnet-${name}'
    location: location
    addressPrefixes: [addressPrefix]
    subnets: [
      {
        name: 'functions'
        addressPrefix: functionsPrefix
        delegation: 'Microsoft.App/environments'
        serviceEndpoints: ['Microsoft.Storage']
      }
      {
        name: 'endpoints'
        addressPrefix: endpointsPrefix
        privateEndpointNetworkPolicies: 'Disabled'
      }
    ]
    tags: tags
    enableTelemetry: false
  }
}

module postgresDns 'br/public:avm/res/network/private-dns-zone:0.8.1' = {
  name: 'postgres-dns'
  params: {
    name: 'privatelink.postgres.database.azure.com'
    virtualNetworkLinks: [
      {
        name: 'runtime'
        virtualNetworkResourceId: vnet.outputs.resourceId
        registrationEnabled: false
      }
    ]
    tags: tags
    enableTelemetry: false
  }
}

output functionsSubnetId string = vnet.outputs.subnetResourceIds[0]
output endpointSubnetId string = vnet.outputs.subnetResourceIds[1]
output postgresDnsZoneId string = postgresDns.outputs.resourceId
