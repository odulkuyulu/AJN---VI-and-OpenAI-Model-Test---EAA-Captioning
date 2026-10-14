targetScope = 'subscription'

@minLength(1)
param environmentName string

param location string

@minLength(1)
param resourceGroupName string = 'rg-${environmentName}'

@description('Object ID of the local user who will invoke the GPT audio deployment.')
param principalId string

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' = {
  name: resourceGroupName
  location: location
  tags: {
    'azd-env-name': environmentName
  }
}

module resources 'resources.bicep' = {
  name: 'ajn-resources'
  scope: resourceGroup
  params: {
    environmentName: environmentName
    location: location
    principalId: principalId
  }
}

output RESOURCE_GROUP_ID string = resourceGroup.id
output AZURE_RESOURCE_GROUP string = resourceGroup.name
output AZURE_LOCATION string = location
output AZURE_OPENAI_ENDPOINT string = resources.outputs.azureOpenAIEndpoint
output AZURE_OPENAI_AUDIO_DEPLOYMENT string = resources.outputs.azureOpenAIAudioDeployment
output AZURE_OPENAI_API_VERSION string = resources.outputs.azureOpenAIApiVersion
output VIDEO_INDEXER_ACCOUNT_ID string = resources.outputs.videoIndexerAccountId
output VIDEO_INDEXER_ACCOUNT_RESOURCE_ID string = resources.outputs.videoIndexerAccountResourceId
output VIDEO_INDEXER_LOCATION string = location

