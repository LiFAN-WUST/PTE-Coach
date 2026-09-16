import {test} from 'node:test';
import assert from 'node:assert/strict';
import {contentGroups,phoneAdvice} from '../../app/static/feedback.js';
test('adjacent edits are explained as a phrase, including insertions',()=>{
 const operations=[{kind:'insertion',spoken:'it',spoken_index:0},{kind:'insertion',spoken:'is',spoken_index:1},{kind:'substitution',reference:'its',spoken:'coming',spoken_index:2},{kind:'substitution',reference:'Commonwealth',spoken:'with',spoken_index:3}];
 const groups=contentGroups({comparison:{operations},features:{words:[{start:1,end:2},{start:2,end:3},{start:3,end:4},{start:4,end:5}]}});
 assert.equal(groups.length,1);assert.equal(groups[0].expected,'its Commonwealth');assert.equal(groups[0].heard,'it is coming with');assert.equal(groups[0].start,1);
});
test('th versus s has plain language but an impossible mapping is not a diagnosis',()=>{
 assert.match(phoneAdvice({phonemes:[{status:'review',expected:'θ',heard:'s'}]}).text,/th.*s/);
 assert.equal(phoneAdvice({phonemes:[{status:'review',expected:'æ',heard:'t'}]}),null);
 assert.equal(phoneAdvice({phonemes:[{status:'uncertain',expected:'θ',heard:'s'}]}),null);
 assert.equal(phoneAdvice({diagnostic_ready:false,phonemes:[{status:'review',expected:'θ',heard:'s'}]}),null);
});
