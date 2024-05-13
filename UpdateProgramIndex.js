// File run by github workflow to update the ProgramIndex.json file.

const fs = require("fs");
const https = require('https');
const fetch = require('node-fetch-commonjs');

// Async function so we can await
(async function main(){
    const response = await (await fetch("https://api.coindesk.com/v1/bpi/currentprice.json")).text()
    fs.writeFileSync('test.txt', response);
    console.log("Finished")
})()

// const url = 'https://api.coindesk.com/v1/bpi/currentprice.json';
// https.get(url, (response) => {
//   let data = '';
//   response.on('data', (chunk) => {
//     data += chunk;
//   });
//   response.on('end', () => {
//     const json = JSON.parse(data);
//     const price = json.bpi.USD.rate_float.toFixed(2);
//     const fileContents = `var price = "${price}";`;
//     fs.writeFile('test.js', fileContents, (err) => {
//       if (err) throw err;
//       console.log('Bitcoin price updated successfully!');
//     });
//   });
// }).on('error', (err) => {
//   console.log('Error: ' + err.message);
// });
