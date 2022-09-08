
import fs from 'fs';
import { GraphQLClient } from 'graphql-request';
import toml from "toml";
import { zencode_exec } from 'zenroom';
import sign from '../crypto/src/sign_graphql.mjs';
import { CREATE_ASSET, CREATE_LOCATION, QUERY_VARIABLES } from './gqlQueries.mjs';
import {
	setTimeout as sleep
} from 'timers/promises';



const USERNAME = "pna";
const EDDSA = 'CpXu6v7EdcajeusmCAfj7CFDnxCtunh4EGSHDCo8Yyed'
const AGENT = '061FKNW40X4CAEEAFSW8NZRCWG'
// const URI = 'http://localhost:3030/graphql'
const URI = 'http://65.109.11.42:8000/api';
const GQLC = new GraphQLClient(URI);

// const pk = "AomVAkMfTjZ3zgwiXwhSykH9j5GG3qbqar6AMh8Zcsgj"

const signRequest = async (query, variables) => {
	const variablesWithoutLineBreaks = JSON.stringify(variables).replace(/\\n/g, '');
	const body = `{"query":"${query}","variables":${variablesWithoutLineBreaks}}`
	const keys = `{"keyring": {"eddsa": "${EDDSA}"}}`
	const data = `{"gql": "${Buffer.from(body, 'utf8').toString('base64')}"}`
	const {result} = await zencode_exec(sign(), {data, keys});
	return {
		'zenflows-sign': JSON.parse(result).eddsa_signature,
		'zenflows-user': USERNAME,
		'zenflows-hash': JSON.parse(result).hash
	}
}

const ql = async ({query, variables={}}) => {
	let requestHeaders = {};
	try {
		requestHeaders = await signRequest(query, variables);
	} catch (err) {
		console.error(err);
	}
	const result = await GQLC.request(query, variables, requestHeaders);
	return result;
}


export const execute = async (filename) => {
	const content = fs.readFileSync(filename, 'utf8');
	const metadata = toml.parse(content);
	const iv = await ql({query: QUERY_VARIABLES,});
	const spec = iv.instanceVariables.specs.specProjectDesign.id
	// const location = metadata.__meta?.source || 'unknown ' + new Date().toUTCString();
	// const loc = await ql({
	// 	query: CREATE_LOCATION,
	// 	variables: {
	// 		name: location,
	// 		addr: location
	// 	}
	// })
	// const locationId = loc.createSpatialThing.spatialThing.id
	const locationId = "061G4Y6M130HN3G9WWEVDGKTR4";
	try {
		console.log(`⚙️ processing ${metadata.name}`);
		await sleep(3000);
		const asset = await ql({
			query: CREATE_ASSET,
			variables: {
				resourceSpec: spec,
				agent: AGENT,
				name: metadata.name,
				metadata: `description: ${metadata.function}, repositoryOrId: ${metadata.repo}`,
				location: locationId,
				oneUnit: iv.instanceVariables.units.unitOne.id,
				creationTime: new Date().toISOString(),
			}
		});
		console.log('ASSET CREATED', JSON.parse(JSON.stringify(asset)))
	} catch (e) {
		console.error(e)
	}
}
