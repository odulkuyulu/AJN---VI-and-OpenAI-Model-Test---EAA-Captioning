param environmentName string
param location string
param principalId string

var resourceToken = uniqueString(subscription().id, resourceGroup().id, location, environmentName)
var storageBlobDataContributorRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
)
var cognitiveServicesOpenAIUserRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
)
var modelDeploymentName = 'gpt-audio-mini-ajn'
var commonTags = {
  application: 'ajn-accessible-captioning'
  environment: environmentName
  workload: 'proof-of-concept'
}

resource deploymentIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: 'azid${resourceToken}'
  location: location
  tags: commonTags
}

resource storage 'Microsoft.Storage/storageAccounts@2025-01-01' = {
  name: 'azst${resourceToken}'
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  tags: commonTags
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
  }
}

resource videoIndexer 'Microsoft.VideoIndexer/accounts@2024-01-01' = {
  name: 'azvi${resourceToken}'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  tags: commonTags
  properties: {
    storageServices: {
      resourceId: storage.id
    }
  }
}

resource videoIndexerStorageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, videoIndexer.id, storageBlobDataContributorRoleId)
  scope: storage
  properties: {
    principalId: videoIndexer.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageBlobDataContributorRoleId
    description: 'Allows Video Indexer to use its dedicated media storage account.'
  }
}

resource aiServices 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: 'azai${resourceToken}'
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  tags: commonTags
  properties: {
    customSubDomainName: 'azai${resourceToken}'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource audioModel 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: aiServices
  name: modelDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 1
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-audio-mini'
      version: '2025-10-06'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
}

resource localUserOpenAIRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServices.id, principalId, cognitiveServicesOpenAIUserRoleId)
  scope: aiServices
  properties: {
    principalId: principalId
    principalType: 'User'
    roleDefinitionId: cognitiveServicesOpenAIUserRoleId
    description: 'Allows the approved local PoC operator to invoke the GPT audio deployment.'
  }
}

output deploymentIdentityResourceId string = deploymentIdentity.id
output azureOpenAIEndpoint string = aiServices.properties.endpoint
output azureOpenAIAudioDeployment string = audioModel.name
output azureOpenAIApiVersion string = '2025-01-01-preview'
output videoIndexerAccountId string = videoIndexer.properties.accountId
output videoIndexerAccountResourceId string = videoIndexer.id

