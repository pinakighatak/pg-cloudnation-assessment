using '../main.bicep'

param environmentName = 'dev'
param databaseAdminObjectId = readEnvironmentVariable('DATABASE_ADMIN_OBJECT_ID')
param databaseAdminName = readEnvironmentVariable('DATABASE_ADMIN_NAME')
param apiClientId = readEnvironmentVariable('API_CLIENT_ID')
param apiAudience = readEnvironmentVariable('API_AUDIENCE')
param allowedCallerClientId = readEnvironmentVariable('AZURE_CLIENT_ID')
param logReaderGroupIds = [readEnvironmentVariable('LOG_READER_GROUP_ID')]
param alertActionGroupId = readEnvironmentVariable('ALERT_ACTION_GROUP_ID')
