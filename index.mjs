#!/usr/bin/env node
import getStdin from 'get-stdin';
import { execute } from './lib/legwork.mjs';

const files = (await getStdin()).split("\n");
let len = files.length-1;

while(len--) {
	await execute(files[len]);
}
