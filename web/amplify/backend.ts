import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource.js';
import { data } from './data/resource.js';
import { storage } from './storage/resource.js';
import { generateSeedData } from './functions/generateSeedData/resource.js';
import { myApiFunction } from './functions/api-functions/resource.js';
import { apiKeyManager } from './functions/api-key-manager/resource.js';
import {
  AuthorizationType,
  Cors,
  LambdaIntegration,
  RestApi,
  CognitoUserPoolsAuthorizer,
} from "aws-cdk-lib/aws-apigateway";
import { Stack } from "aws-cdk-lib";
import { Effect, PolicyStatement } from "aws-cdk-lib/aws-iam";

const backend = defineBackend({
  auth,
  data,
  storage,
  generateSeedData,
  myApiFunction,
  apiKeyManager
}); 

// create a new API stack
const apiStack = backend.createStack("api-stack");

// create a new REST API
const starfishApi = new RestApi(apiStack, "StarfishApi", {
  restApiName: "StarfishApi",
  deploy: true,
  defaultCorsPreflightOptions: {
    allowOrigins: Cors.ALL_ORIGINS, // Restrict this to domains you trust
    allowMethods: Cors.ALL_METHODS, // Specify only the methods you need to allow
    allowHeaders: Cors.DEFAULT_HEADERS, // Specify only the headers you need to allow
  },
});

// Create a Cognito authorizer
const cognitoAuthorizer = new CognitoUserPoolsAuthorizer(apiStack, 'CognitoAuthorizer', {
  cognitoUserPools: [backend.auth.resources.userPool],
});

// Get the API ID
const apiId = starfishApi.restApiId;

// In Amplify Gen2, we need to use a different approach to set environment variables
// We'll use the environment property of the Lambda function in the resource.ts file
// and then update it in the backend.ts file using the addEnvironment method
// This is a workaround for the linter error

// create Lambda integrations
const lambdaIntegration = new LambdaIntegration(
  backend.myApiFunction.resources.lambda
);

const apiKeyManagerIntegration = new LambdaIntegration(
  backend.apiKeyManager.resources.lambda
);

// Add IAM permissions to the API Key Manager Lambda function
backend.apiKeyManager.resources.lambda.addToRolePolicy(
  new PolicyStatement({
    effect: Effect.ALLOW,
    actions: [
      'apigateway:POST',
      'apigateway:GET',
      'apigateway:DELETE',
      'apigateway:PUT',
      'apigateway:PATCH'
    ],
    resources: [
      'arn:aws:apigateway:*::/apikeys',
      'arn:aws:apigateway:*::/apikeys/*',
      'arn:aws:apigateway:*::/usageplans',
      'arn:aws:apigateway:*::/usageplans/*',
      'arn:aws:apigateway:*::/usageplans/*/keys',
      'arn:aws:apigateway:*::/usageplans/*/keys/*'
    ]
  })
);

// Add permission to list REST APIs
backend.apiKeyManager.resources.lambda.addToRolePolicy(
  new PolicyStatement({
    effect: Effect.ALLOW,
    actions: [
      'apigateway:GET'
    ],
    resources: [
      'arn:aws:apigateway:*::/restapis'
    ]
  })
);

// Create a single v1 resource with Cognito authorization
const v1Path = starfishApi.root.addResource("v1");

// API key management endpoints under v1
const apiKeysPath = v1Path.addResource("apikeys", {
  defaultMethodOptions: {
    authorizationType: AuthorizationType.COGNITO,
    authorizer: cognitoAuthorizer,
  }
});

apiKeysPath.addMethod("POST", apiKeyManagerIntegration, {
  operationName: "CreateApiKey",
  apiKeyRequired: false
});

apiKeysPath.addMethod("GET", apiKeyManagerIntegration, {
  operationName: "ListApiKeys",
  apiKeyRequired: false
});

apiKeysPath.addResource("{keyId}").addMethod("DELETE", apiKeyManagerIntegration, {
  operationName: "DeleteApiKey",
  apiKeyRequired: false
});

// Existing endpoints with API key requirement
const generateDataPath = starfishApi.root.addResource("api");

// Add other v1 endpoints
v1Path.addResource("generateData").addMethod("POST", lambdaIntegration, {
  apiKeyRequired: true,
});

v1Path.addResource("jobStatus").addMethod("POST", lambdaIntegration, {
  apiKeyRequired: true
});

v1Path.addResource("data").addMethod("POST", lambdaIntegration, {
  apiKeyRequired: true
});

v1Path.addResource("evaluateData").addMethod("POST", lambdaIntegration, {
  apiKeyRequired: true
});

// add outputs to the configuration file
backend.addOutput({
  custom: {
    API: {
      [starfishApi.restApiName]: {
        endpoint: starfishApi.url,
        region: Stack.of(starfishApi).region,
        apiName: starfishApi.restApiName,
        apiId: apiId, // Add the API ID to the outputs
      },
    },
  },
});