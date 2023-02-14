QUERY_VARIABLES ="""
    query {
      instanceVariables{
        specs{
          specCurrency {
            id
          }
          specProjectDesign {
            id
          }
          specProjectProduct {
            id
          }
          specProjectService {
            id
          }
        }
        units {
          unitOne {
            id
          }
        }
      }
    }
"""

CREATE_PROPOSAL = """
    mutation {
      createProposal(proposal: {
        name: "price tag",
        unitBased: true
      }) 
      {
        proposal {
          id
        }
      }
    }
"""

CREATE_INTENT = """
    mutation (
      $agent: ID!,
      $resource: ID!,
      $oneUnit: ID!,
      $currency: ID!,
      $howMuch: Int!
    ) 
    {
      item: createIntent(
        intent: {
          name: "project",
          action: "transfer",
          provider: $agent,
          resourceInventoriedAs: $resource,
          resourceQuantity: { hasNumericalValue: 1, hasUnit: $oneUnit }
        }
      )
      {
        intent {
          id
        }
      }
      payment: createIntent(
        intent: {
          name: "payment",
          action: "transfer",
          receiver: $agent,
          resourceConformsTo: $currency,
          resourceQuantity: { hasNumericalValue: $howMuch, hasUnit: $oneUnit }
        }
      ) 
      {
        intent {
          id
        }
      }
    }
"""

LINK_PROPOSAL_AND_INTENT = """
    mutation ($proposal: ID!, $item: ID!, $payment: ID!) {
      linkItem: proposeIntent(
        publishedIn: $proposal
        publishes: $item
        reciprocal: false
      ) 
      {
        proposedIntent {
          id
        }
      }
      linkPayment: proposeIntent(
        publishedIn: $proposal
        publishes: $payment
        reciprocal: true
      )
      {
        proposedIntent {
          id
        }
      }
    }
"""

CREATE_LOCATION = """
    mutation ($name: String!, $addr: String!) {
      createSpatialThing(spatialThing: { name: $name, mappableAddress: $addr }) {
        spatialThing {
          id
        }
      }
    }
"""

CREATE_ASSET = """
    mutation (
      $name: String!,
      $note: String,
      $okhv: String,
      $version: String,
      $repo: String,
      $license: String,
      $licensor: String,
      $resourceMetadata: JSONObject,
      $agent: ID!,
      $creationTime: DateTime!,
      $location: ID!,
      $tags: [URI!],
      $resourceSpec: ID!,
      $oneUnit: ID!,
      $images: [IFile!]
    ) 
    {
      createEconomicEvent(
        event: {
          action: "raise",
          resourceMetadata: $resourceMetadata,
          provider: $agent,
          receiver: $agent,
          hasPointInTime: $creationTime,
          resourceClassifiedAs: $tags,
          resourceConformsTo: $resourceSpec,
          resourceQuantity: { hasNumericalValue: 1, hasUnit: $oneUnit },
          toLocation: $location
        }
        newInventoriedResource: { 
          name: $name,
          note: $note,
          images: $images,
          okhv: $okhv,
          version: $version,
          repo: $repo,
          license: $license,
          licensor: $licensor }
      ) 
      {
        economicEvent {
          id
          resourceInventoriedAs {
            id
          }
        }
      }
    }
"""
