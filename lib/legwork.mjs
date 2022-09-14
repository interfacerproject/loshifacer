
import fs from 'fs';
import { GraphQLClient } from 'graphql-request';
import toml from "toml";
import { zencode_exec } from 'zenroom';
import sign from '../crypto/src/sign_graphql.mjs';
import { CREATE_ASSET, CREATE_LOCATION, QUERY_VARIABLES } from './gqlQueries.mjs';
import {
	setTimeout as sleep
} from 'timers/promises';



const USERNAME = "matteo";
const EDDSA = '2dYy36i7e34uMtzVu8i2NHfzPwpW89RQayWJtub7Urio';
const AGENT = '061KFE1AADXNDYTXRYTG007A14';
// testing instance
const URI = 'http://65.109.11.42:9000/api';
const GQLC = new GraphQLClient(URI);

const signRequest = async (query, variables) => {
	const variablesWithoutLineBreaks = JSON.stringify(variables).replace(/\\\\n|\\n/g, '');
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
	if( fs.lstatSync(filename).isDirectory() ) { return; }
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
	const locationId = "061KFEJCA035RE8TSAYDN6DVDC";
	try {
		console.log(`⚙️ processing ${metadata.name}`);
		await sleep(3000);
		const asset = await ql({
			query: CREATE_ASSET,
			variables: {
				name: metadata.name,
				note: metadata.function,
				okhv: metadata.okhv,
				version: metadata.version,
				repo: metadata.repo,
				license: metadata.license,
				licensor: Array.isArray(metadata.licensor)?
					metadata.licensor[0] : metadata.licensor,
				metadata: JSON.stringify(metadata),
				resourceSpec: spec,
				agent: AGENT,
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
